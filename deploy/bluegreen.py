#!/usr/bin/env python3
"""Blue-green deploys for Notifaybers on a host with Podman and a Caddy container.

Two slots, "blue" and "green", each a container on its own loopback port. One is live;
a deploy builds the new commit, starts it in the idle slot, waits until it is healthy,
repoints Caddy at it with a graceful reload, then stops the old slot. If anything fails
before the switch, the live slot is never touched. The stopped old slot is kept so
`rollback` is instant.

    bluegreen.py watch              poll the git remote and deploy new commits (run at boot)
    bluegreen.py deploy [--sha X]   deploy the remote branch head (or X) now; --force to redeploy
    bluegreen.py rollback           switch back to the previous slot
    bluegreen.py boot               start the live slot's container (run at boot)
    bluegreen.py status             show what is live

Configuration: $NOTIFAYBERS_HOME/shared/deploy.env (KEY=VALUE lines) or the environment.
Standard library only. See the "Auto-deploy" section of README.md.
"""
import argparse
import fcntl
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HOME = Path(os.environ.get("NOTIFAYBERS_HOME", "/opt/notifaybers"))
SHARED = HOME / "shared"
STATE_FILE = SHARED / "state.json"
os.environ.setdefault("PODMAN_IGNORE_CGROUPSV1_WARNING", "1")

SLOTS = ("blue", "green")
IMAGE = "notifaybers"


def load_conf() -> dict:
    conf = {
        "DOMAIN": "",
        "BRANCH": "master",
        "BLUE_PORT": "18110",
        "GREEN_PORT": "18111",
        "CADDY_CONTAINER": "caddy",
        "CADDY_SNIPPET": "",  # file Caddy imports; written on every switch
        "CADDY_CONFIG": "/etc/caddy/Caddyfile",
        "ENGINE": "podman",
        "POLL_SECONDS": "60",
        "KEEP_RELEASES": "4",
        "REPO_DIR": str(HOME / "repo"),
        "DEPLOY_KEY": str(SHARED / "ssh" / "deploy_key"),
        "HEALTH_TIMEOUT": "180",
    }
    path = SHARED / "deploy.env"
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                conf[key.strip()] = value.strip().strip("\"'")
    for key in conf:
        if key in os.environ:
            conf[key] = os.environ[key]
    return conf


C = load_conf()
ENGINE = C["ENGINE"]
REPO = Path(C["REPO_DIR"])


def log(msg: str) -> None:
    print(time.strftime("%Y-%m-%d %H:%M:%S"), msg, flush=True)


def run(cmd, check=True, capture=False, cwd=None, env=None, input=None, merge=False):
    """Run a command. capture=True returns stdout (stderr kept apart, podman warns on it);
    merge=True folds stderr into stdout (for container logs)."""
    result = subprocess.run(
        cmd, check=False, text=True, cwd=cwd, env=env, input=input,
        stdout=subprocess.PIPE if capture else None,
        stderr=(subprocess.STDOUT if merge else subprocess.PIPE) if capture else None,
    )
    if check and result.returncode != 0:
        out = f"\n{(result.stdout or '').strip()}\n{(result.stderr or '').strip()}" if capture else ""
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(map(str, cmd))}{out}")
    if capture:
        result.stdout = (result.stdout or '').strip()
    return result


# ---- state -----------------------------------------------------------------------------

def read_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except (OSError, ValueError):
        return {}


def write_state(state: dict) -> None:
    SHARED.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2))
    tmp.replace(STATE_FILE)


def port_of(slot: str) -> int:
    return int(C[f"{slot.upper()}_PORT"])


def name_of(slot: str) -> str:
    return f"notifaybers-{slot}"


def other(slot: str) -> str:
    return "green" if slot == "blue" else "blue"


# ---- git -------------------------------------------------------------------------------

def git_env() -> dict:
    env = dict(os.environ)
    key = Path(C["DEPLOY_KEY"])
    if key.exists():
        known = SHARED / "ssh" / "known_hosts"
        env["GIT_SSH_COMMAND"] = (
            f"ssh -i {key} -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new "
            f"-o UserKnownHostsFile={known} -o BatchMode=yes -o ConnectTimeout=15"
        )
    return env


def remote_head() -> str:
    run(["git", "-C", str(REPO), "fetch", "--quiet", "origin", C["BRANCH"]], env=git_env())
    return run(["git", "-C", str(REPO), "rev-parse", "FETCH_HEAD"], capture=True).stdout


def export_release(sha: str) -> Path:
    dest = HOME / "releases" / sha[:12]
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    archive = subprocess.Popen(["git", "-C", str(REPO), "archive", sha], stdout=subprocess.PIPE)
    untar = subprocess.run(["tar", "-x", "-C", str(dest)], stdin=archive.stdout)
    archive.stdout.close()
    if archive.wait() != 0 or untar.returncode != 0:
        raise RuntimeError(f"could not export {sha[:12]} from the repository")
    # The image has no git history; this is what Settings shows as the version.
    label = run(["git", "-C", str(REPO), "log", "-1", "--format=%h · %cs", sha], capture=True).stdout
    (dest / "VERSION").write_text(label + "\n")
    return dest


# ---- containers ------------------------------------------------------------------------

def container_running(name: str) -> bool:
    r = run([ENGINE, "inspect", "-f", "{{.State.Running}}", name], check=False, capture=True)
    return r.stdout == "true"


def container_exists(name: str) -> bool:
    return run([ENGINE, "container", "exists", name], check=False).returncode == 0


def http_get(url: str, timeout: float = 5):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, ""
    except (urllib.error.URLError, OSError, TimeoutError):
        return 0, ""


def wait_healthy(slot: str) -> None:
    deadline = time.time() + int(C["HEALTH_TIMEOUT"])
    url = f"http://127.0.0.1:{port_of(slot)}/healthz"
    while time.time() < deadline:
        if not container_running(name_of(slot)):
            break
        status, body = http_get(url)
        if status == 200:
            try:
                if json.loads(body).get("slot") == slot:
                    return
            except ValueError:
                pass
        time.sleep(2)
    logs = subprocess.run([ENGINE, "logs", "--tail", "40", name_of(slot)], text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout
    raise RuntimeError(f"{slot} did not become healthy. Last logs:\n{logs}")


def start_slot(slot: str, sha12: str) -> None:
    name = name_of(slot)
    run([ENGINE, "rm", "-f", name], check=False, capture=True)
    run([
        ENGINE, "run", "-d", "--name", name, "--restart", "unless-stopped", "--network", "host",
        "--log-opt", "max-size=5mb",
        "--env-file", str(SHARED / ".env"),
        "-e", f"DEPLOY_SLOT={slot}",
        "-v", f"{SHARED / 'data'}:/app/data",
        f"{IMAGE}:{sha12}",
        "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port_of(slot)), "--workers", "1",
    ], capture=True)


# ---- caddy -----------------------------------------------------------------------------

def snippet_text(slot: str) -> str:
    return (
        f"# Managed by deploy/bluegreen.py (live slot: {slot}). Do not edit.\n"
        f"{C['DOMAIN']} {{\n"
        "    encode zstd gzip\n"
        "    header {\n"
        "        X-Content-Type-Options nosniff\n"
        "        Referrer-Policy strict-origin-when-cross-origin\n"
        '        Strict-Transport-Security "max-age=31536000"\n'
        "    }\n"
        f"    reverse_proxy 127.0.0.1:{port_of(slot)}\n"
        "}\n"
    )


def caddy(*args) -> None:
    run([ENGINE, "exec", C["CADDY_CONTAINER"], "caddy", *args, "--config", C["CADDY_CONFIG"]], capture=True)


def point_caddy_at(slot: str) -> None:
    """Swap the upstream and reload Caddy gracefully; put the old file back if Caddy refuses."""
    path = Path(C["CADDY_SNIPPET"])
    old = path.read_text() if path.exists() else None
    tmp = path.with_suffix(".tmp-notifaybers")
    tmp.write_text(snippet_text(slot))
    try:
        # Written beside the real file under a name the glob import does not match,
        # so a half-written file is never loaded.
        tmp.replace(path)
        caddy("validate", "--adapter", "caddyfile")
        caddy("reload", "--adapter", "caddyfile")
    except Exception:
        if old is None:
            path.unlink(missing_ok=True)
        else:
            path.write_text(old)
        raise


def live_slot_via_caddy() -> str:
    """Ask the public hostname (through Caddy, on this host) which slot answers."""
    out = run(
        ["curl", "-sk", "-m", "8", "--resolve", f"{C['DOMAIN']}:443:127.0.0.1", f"https://{C['DOMAIN']}/healthz"],
        check=False, capture=True,
    ).stdout
    try:
        return json.loads(out).get("slot", "")
    except ValueError:
        return ""


def wait_caddy_serves(slot: str, seconds: int = 90) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if live_slot_via_caddy() == slot:
            return True
        time.sleep(3)
    return False


# ---- operations ------------------------------------------------------------------------

class Locked(Exception):
    pass


def lock():
    SHARED.mkdir(parents=True, exist_ok=True)
    handle = open(SHARED / "deploy.lock", "a")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise Locked()
    return handle


def cut_over(new: str, old: str | None) -> None:
    """Point Caddy at `new`, confirm it answers, then retire `old`. Reverts Caddy on failure."""
    point_caddy_at(new)
    if not wait_caddy_serves(new):
        # With no previous slot (first deploy) the certificate may still be arriving; only revert if one existed.
        if old and container_running(name_of(old)):
            point_caddy_at(old)
            raise RuntimeError(f"Caddy did not serve {new} after the switch; switched back to {old}")
        log(f"warning: could not confirm {C['DOMAIN']} through Caddy (certificate may still be issuing)")
    if old and container_exists(name_of(old)):
        time.sleep(5)  # let in-flight requests finish
        run([ENGINE, "stop", "-t", "30", name_of(old)], check=False, capture=True)


def wait_scheduler(slot: str, seconds: int = 90) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        status, body = http_get(f"http://127.0.0.1:{port_of(slot)}/healthz")
        if status == 200 and json.loads(body or "{}").get("scheduler"):
            return True
        time.sleep(2)
    return False


def prune(state: dict) -> None:
    keep = []
    for sha in [state.get("sha"), (state.get("previous") or {}).get("sha"), *state.get("history", [])]:
        if sha and sha[:12] not in keep:
            keep.append(sha[:12])
    keep = keep[: int(C["KEEP_RELEASES"])]
    releases = HOME / "releases"
    if releases.exists():
        for entry in releases.iterdir():
            if entry.name not in keep:
                shutil.rmtree(entry, ignore_errors=True)
    tags = run([ENGINE, "images", IMAGE, "--format", "{{.Tag}}"], check=False, capture=True).stdout.split()
    for tag in tags:
        if tag not in keep:
            # Only this app's own tags; never a prune of dangling layers (other apps share the engine).
            run([ENGINE, "rmi", f"{IMAGE}:{tag}"], check=False, capture=True)


def deploy(sha: str | None, force: bool) -> int:
    try:
        guard = lock()
    except Locked:
        log("another deploy is running; exiting")
        return 0
    state = read_state()
    try:
        if sha is None:
            sha = remote_head()
        run(["git", "-C", str(REPO), "reset", "--hard", "--quiet", sha])
        sha12 = sha[:12]
        active = state.get("active")
        if not force and state.get("sha") == sha and active and container_running(name_of(active)):
            log(f"already live: {sha12}")
            return 0

        log(f"deploying {sha12} (live: {active or 'nothing'} {str(state.get('sha', ''))[:12]})")
        src = export_release(sha)
        run([ENGINE, "build", "--network", "host", "-t", f"{IMAGE}:{sha12}", str(src)])

        new = other(active) if active else "blue"
        start_slot(new, sha12)
        try:
            wait_healthy(new)
            status, _ = http_get(f"http://127.0.0.1:{port_of(new)}/login")
            if status != 200:
                raise RuntimeError(f"smoke test: /login returned {status}")
            cut_over(new, active)
        except Exception:
            log(f"{new} failed; keeping {active or 'nothing'} live")
            run([ENGINE, "rm", "-f", name_of(new)], check=False, capture=True)
            raise

        history = [sha, *[h for h in state.get("history", []) if h != sha]]
        state = {
            "active": new, "sha": sha, "deployed_at": int(time.time()),
            "previous": {"slot": active, "sha": state.get("sha")} if active else None,
            "history": history[:8],
        }
        write_state(state)
        if not wait_scheduler(new):
            log("warning: scheduler not running yet on the new slot (is the old one still stopping?)")
        prune(state)
        log(f"live: {new} {sha12}")
        return 0
    except Exception as exc:
        log(f"DEPLOY FAILED for {str(sha)[:12]}: {exc}")
        if sha:
            state = read_state()
            state["failed_sha"] = sha
            write_state(state)
        return 1
    finally:
        guard.close()


def rollback() -> int:
    try:
        guard = lock()
    except Locked:
        log("another deploy is running; exiting")
        return 1
    try:
        state = read_state()
        prev = state.get("previous")
        if not prev or not container_exists(name_of(prev["slot"])):
            log("nothing to roll back to")
            return 1
        cur, back = state["active"], prev["slot"]
        run([ENGINE, "start", name_of(back)], capture=True)
        wait_healthy(back)
        cut_over(back, cur)
        state.update({"active": back, "sha": prev["sha"], "previous": {"slot": cur, "sha": state["sha"]}})
        write_state(state)
        log(f"rolled back: live is {back} {str(prev['sha'])[:12]}")
        return 0
    except Exception as exc:
        log(f"ROLLBACK FAILED: {exc}")
        return 1
    finally:
        guard.close()


def boot() -> int:
    state = read_state()
    active = state.get("active")
    if not active:
        log("nothing deployed yet")
        return 0
    if not container_running(name_of(active)):
        run([ENGINE, "start", name_of(active)], capture=True)
    log(f"live slot {active} started")
    return 0


def status() -> int:
    state = read_state()
    print(json.dumps(state, indent=2))
    for slot in SLOTS:
        name = name_of(slot)
        if container_exists(name):
            http, body = http_get(f"http://127.0.0.1:{port_of(slot)}/healthz", timeout=3)
            print(f"{slot}: {'running' if container_running(name) else 'stopped'} port {port_of(slot)} http={http} {body.strip()}")
        else:
            print(f"{slot}: no container")
    print(f"public: {live_slot_via_caddy() or 'no answer'} via {C['DOMAIN']}")
    return 0


def watch() -> int:
    log(f"watching {C['BRANCH']} every {C['POLL_SECONDS']}s")
    while True:
        try:
            head = remote_head()
            state = read_state()
            if head != state.get("sha") and head != state.get("failed_sha"):
                # Move the checkout first so the new commit is deployed by its own deploy script.
                run(["git", "-C", str(REPO), "reset", "--hard", "--quiet", head])
                run([sys.executable, str(Path(__file__).resolve()), "deploy", "--sha", head], check=False)
        except Exception as exc:  # network blips must not kill the loop
            log(f"poll error: {exc}")
        time.sleep(int(C["POLL_SECONDS"]))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("deploy")
    d.add_argument("--sha")
    d.add_argument("--force", action="store_true")
    for name in ("watch", "rollback", "boot", "status"):
        sub.add_parser(name)
    args = parser.parse_args()
    if args.cmd != "boot" and args.cmd != "status" and not C["DOMAIN"]:
        sys.exit("DOMAIN is not set (shared/deploy.env)")
    if args.cmd in ("deploy", "rollback", "watch") and not C["CADDY_SNIPPET"]:
        sys.exit("CADDY_SNIPPET is not set (shared/deploy.env)")
    if args.cmd == "deploy":
        return deploy(args.sha, args.force)
    return {"watch": watch, "rollback": rollback, "boot": boot, "status": status}[args.cmd]()


if __name__ == "__main__":
    sys.exit(main())
