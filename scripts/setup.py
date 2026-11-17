#!/usr/bin/env python3
"""Interactive setup for Notifaybers.

    python3 scripts/setup.py

Asks for everything the app needs (explaining where to get each value), writes
.env, generates the secret key and Web Push (VAPID) keys, and can start the app.
Safe to re-run: existing values are offered as defaults and nothing is
overwritten without asking. Needs only Python 3.9+; openssl or Docker are used
when available.
"""

from __future__ import annotations

import base64
import getpass
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, available_timezones

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"
DATA_DIR = ROOT / "data"
VAPID_PATH = DATA_DIR / "vapid_private.pem"

USE_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text


def bold(t: str) -> str: return c("1", t)
def dim(t: str) -> str: return c("2", t)
def green(t: str) -> str: return c("32", t)
def yellow(t: str) -> str: return c("33", t)
def red(t: str) -> str: return c("31", t)
def cyan(t: str) -> str: return c("36", t)


def step(n: int, total: int, title: str) -> None:
    print()
    print(bold(cyan(f"[{n}/{total}] {title}")))


def info(text: str) -> None:
    for line in text.strip("\n").splitlines():
        print("  " + line)


def ok(text: str) -> None:
    print("  " + green("✓ ") + text)


def warn(text: str) -> None:
    print("  " + yellow("! ") + text)


def die(text: str) -> None:
    print(red("Error: ") + text)
    sys.exit(1)


# --------------------------------------------------------------------------
# Prompts
# --------------------------------------------------------------------------

def ask(label: str, default: str | None = None, *, validate=None, secret: bool = False,
        required: bool = True, hint: str | None = None) -> str:
    """Prompt until valid. Empty input takes the default. Secrets are not echoed."""
    shown = default
    if default and secret:
        shown = mask(default)
    suffix = f" [{shown}]" if shown else ("" if required else " (optional, Enter to skip)")
    while True:
        prompt = f"  {bold(label)}{suffix}: "
        try:
            raw = getpass.getpass(prompt) if secret else input(prompt)
        except EOFError:
            die("Input ended before setup finished.")
        value = raw.strip() or (default or "")
        if not value:
            if required:
                warn("A value is required." + (f" {hint}" if hint else ""))
                continue
            return ""
        if validate:
            problem = validate(value)
            if problem:
                warn(problem)
                continue
        return value


def confirm(label: str, default: bool = True) -> bool:
    hint = "Y/n" if default else "y/N"
    while True:
        try:
            raw = input(f"  {bold(label)} [{hint}]: ").strip().lower()
        except EOFError:
            die("Input ended before setup finished.")
        if not raw:
            return default
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        warn("Please answer y or n.")


def choose(label: str, options: list[tuple[str, str]], default: int = 1) -> int:
    for i, (title, desc) in enumerate(options, 1):
        print(f"    {bold(str(i))}) {title}  {dim(desc)}")
    while True:
        try:
            raw = input(f"  {bold(label)} [{default}]: ").strip()
        except EOFError:
            die("Input ended before setup finished.")
        if not raw:
            return default
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw)
        warn(f"Enter a number from 1 to {len(options)}.")


def mask(value: str) -> str:
    return value[:4] + "…" + value[-3:] if len(value) > 10 else "•" * len(value)


# --------------------------------------------------------------------------
# Validators
# --------------------------------------------------------------------------

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def v_email(value: str) -> str | None:
    return None if EMAIL_RE.match(value) else "That doesn't look like an email address."


def v_emails(value: str) -> str | None:
    for part in value.split(","):
        if part.strip() and not EMAIL_RE.match(part.strip()):
            return f"'{part.strip()}' doesn't look like an email address."
    return None


def v_https_origin(value: str) -> str | None:
    value = value.rstrip("/")
    if not re.match(r"^https://[A-Za-z0-9.-]+(:\d+)?$", value):
        return "Use the origin only, starting with https://, no path or trailing slash (e.g. https://notify.example.com)."
    return None


def v_timezone(value: str) -> str | None:
    try:
        ZoneInfo(value)
    except Exception:
        return "Unknown timezone. Use an IANA name like Europe/London or America/New_York."
    return None


def v_port(value: str) -> str | None:
    return None if value.isdigit() and 1 <= int(value) <= 65535 else "Enter a port between 1 and 65535."


def v_int_min(minimum: int):
    def check(value: str) -> str | None:
        return None if value.isdigit() and int(value) >= minimum else f"Enter a whole number, at least {minimum}."
    return check


def v_google_id(value: str) -> str | None:
    return None if value.endswith(".apps.googleusercontent.com") else (
        "A Google client ID ends in .apps.googleusercontent.com. Copy it again from the credentials page.")


# --------------------------------------------------------------------------
# .env handling
# --------------------------------------------------------------------------

def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        values[key.strip()] = val.strip().strip('"').strip("'")
    return values


MANAGED_KEYS = [
    "SECRET_KEY", "ADMIN_USERNAME", "DEFAULT_TIMEZONE", "DATABASE_URL",
    "PUBLIC_BASE_URL", "SESSION_SECURE_COOKIE", "SESSION_MAX_AGE_DAYS",
    "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "ADMIN_EMAIL", "ALLOWED_EMAILS", "OPEN_SIGNUP",
    "DEV_AUTO_LOGIN",
    "VAPID_PUBLIC_KEY", "VAPID_PRIVATE_KEY_PATH", "VAPID_SUBJECT",
    "WATCHDOG_MIN_PING_SECONDS", "WEBHOOK_RATE_LIMIT_PER_MINUTE",
]


def render_env(v: dict[str, str], extras: dict[str, str]) -> str:
    def line(key: str) -> str:
        return f"{key}={v.get(key, '')}"

    parts = [
        "# Generated by scripts/setup.py. Edit freely, or re-run the script.",
        "",
        "# --- Core ---",
        "# Signs session cookies. Changing it logs everyone out.",
        line("SECRET_KEY"),
        "# Name of the account created on first startup (you sign in with Google).",
        line("ADMIN_USERNAME"),
        line("DEFAULT_TIMEZONE"),
        line("DATABASE_URL"),
        "",
        "# --- Public address ---",
        "# Shown in webhook / watchdog snippets and used for the Google redirect.",
        line("PUBLIC_BASE_URL"),
        line("SESSION_SECURE_COOKIE"),
        line("SESSION_MAX_AGE_DAYS"),
        "",
        "# --- Sign in with Google ---",
        line("GOOGLE_CLIENT_ID"),
        line("GOOGLE_CLIENT_SECRET"),
        "# Your Google email: links the seeded account to your Google login.",
        line("ADMIN_EMAIL"),
        "# Other Google emails allowed in, comma-separated.",
        line("ALLOWED_EMAILS"),
        "# true = any verified Google account may sign up.",
        line("OPEN_SIGNUP"),
        "# LOCAL DEBUGGING ONLY: /login on localhost signs you in without Google.",
        line("DEV_AUTO_LOGIN"),
        "",
        "# --- Web Push (VAPID) ---",
        line("VAPID_PUBLIC_KEY"),
        line("VAPID_PRIVATE_KEY_PATH"),
        line("VAPID_SUBJECT"),
        "",
        "# --- Limits ---",
        line("WATCHDOG_MIN_PING_SECONDS"),
        line("WEBHOOK_RATE_LIMIT_PER_MINUTE"),
    ]
    if extras:
        parts += ["", "# --- Other settings kept from your previous .env ---"]
        parts += [f"{k}={val}" for k, val in extras.items()]
    return "\n".join(parts) + "\n"


# --------------------------------------------------------------------------
# VAPID keys
# --------------------------------------------------------------------------

def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def vapid_public_from_pem(path: Path) -> str | None:
    """Return the base64url uncompressed public key for an EC private key PEM."""
    try:
        from cryptography.hazmat.primitives import serialization
        key = serialization.load_pem_private_key(path.read_bytes(), password=None)
        raw = key.public_key().public_bytes(
            serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
        return _b64url(raw)
    except ImportError:
        pass
    except Exception:
        return None
    if shutil.which("openssl"):
        res = subprocess.run(["openssl", "ec", "-in", str(path), "-pubout", "-outform", "DER"],
                             capture_output=True)
        if res.returncode == 0 and len(res.stdout) >= 65:
            return _b64url(res.stdout[-65:])
    return None


def generate_vapid(path: Path) -> str | None:
    """Create a new P-256 key at path (mode 600) and return its public key."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        key = ec.generate_private_key(ec.SECP256R1())
        path.write_bytes(key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption()))
    except ImportError:
        if not shutil.which("openssl"):
            return None
        res = subprocess.run(["openssl", "ecparam", "-name", "prime256v1", "-genkey", "-noout",
                              "-out", str(path)], capture_output=True)
        if res.returncode != 0:
            return None
    os.chmod(path, 0o600)
    return vapid_public_from_pem(path)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def detect_timezone() -> str:
    tz = os.environ.get("TZ")
    if tz and tz in available_timezones():
        return tz
    try:
        target = os.path.realpath("/etc/localtime")
        if "zoneinfo/" in target:
            name = target.split("zoneinfo/", 1)[1]
            if name in available_timezones():
                return name
    except OSError:
        pass
    return "UTC"


def run(cmd: list[str], **kw) -> int:
    print(dim("  $ " + " ".join(cmd)))
    return subprocess.run(cmd, cwd=ROOT, **kw).returncode


def wait_for(url: str, seconds: int = 90) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(2)
    return False


def have_docker_compose() -> bool:
    if not shutil.which("docker"):
        return False
    return subprocess.run(["docker", "compose", "version"], capture_output=True).returncode == 0


# --------------------------------------------------------------------------
# Main flow
# --------------------------------------------------------------------------

def main() -> None:
    if sys.version_info < (3, 9):
        die("Python 3.9 or newer is required.")
    os.chdir(ROOT)

    print()
    print(bold("Notifaybers setup"))
    info("""
I'll ask a few questions, explain where to find each answer, then write .env,
generate your keys and (optionally) start the app. Press Enter to accept a
[default]. Nothing leaves this machine. You can re-run this any time.
""")

    existing = read_env(ENV_PATH)
    if existing:
        warn(f"Found an existing .env ({len(existing)} settings). Its values are offered as defaults.")

    total = 6

    # ---- 1. Where will it run -------------------------------------------
    step(1, total, "Where will Notifaybers run?")
    mode_default = 2 if existing.get("DATABASE_URL", "").startswith("sqlite:////app") else 1
    mode = choose("Choose", [
        ("This computer, for development", "http://localhost, no HTTPS, optional login shortcut"),
        ("A server (Docker + HTTPS domain)", "what you want for real use, notifications need HTTPS"),
    ], mode_default)
    local = mode == 1

    v: dict[str, str] = {}

    # ---- 2. Address ---------------------------------------------------------
    step(2, total, "Address")
    if local:
        port = ask("Local port", "8000", validate=v_port)
        v["PUBLIC_BASE_URL"] = f"http://localhost:{port}"
        v["SESSION_SECURE_COOKIE"] = "false"
        ok(f"Will run at {v['PUBLIC_BASE_URL']}")
    else:
        info("""
The public address people (and your phone) will open. You need a domain whose
DNS A record points at this server, and a reverse proxy (Caddy, nginx) giving
it HTTPS: Web Push and Google sign-in both require HTTPS.
""")
        default_url = existing.get("PUBLIC_BASE_URL", "")
        if default_url.startswith("http://") or "example.com" in default_url:
            default_url = ""
        v["PUBLIC_BASE_URL"] = ask("Public URL", default_url or None, validate=v_https_origin,
                                   hint="e.g. https://notify.example.com").rstrip("/")
        v["SESSION_SECURE_COOKIE"] = "true"
        port = "8000"

    # ---- 3. You -------------------------------------------------------------
    step(3, total, "You")
    info("""
Notifaybers signs in with Google only. Your Google email links to the account
created on first start, so it's the one that owns your reminders and settings.
""")
    v["ADMIN_EMAIL"] = ask("Your Google email", existing.get("ADMIN_EMAIL") or None, validate=v_email,
                           required=not local, hint="Needed so you can sign in.")
    v["ADMIN_USERNAME"] = existing.get("ADMIN_USERNAME") or "admin"
    v["DEFAULT_TIMEZONE"] = ask("Timezone", existing.get("DEFAULT_TIMEZONE") or detect_timezone(),
                                validate=v_timezone,
                                hint="Reminders fire in this timezone. Each user can change theirs in Settings.")
    v["ALLOWED_EMAILS"] = ask("Other Google emails allowed to sign in, comma-separated",
                              existing.get("ALLOWED_EMAILS") or None, validate=v_emails, required=False)
    v["OPEN_SIGNUP"] = "true" if confirm(
        "Let ANY Google account sign up? (no for a private instance)",
        existing.get("OPEN_SIGNUP", "false").lower() == "true") else "false"

    # ---- 4. Google ----------------------------------------------------------
    step(4, total, "Sign in with Google")
    callback = f"{v['PUBLIC_BASE_URL']}/auth/google/callback"
    redirects = [callback]
    if local:
        redirects = [f"http://localhost:{port}/auth/google/callback",
                     f"http://127.0.0.1:{port}/auth/google/callback"]
    info(f"""
You need a free Google OAuth client. About 5 minutes:

  1. Open {cyan('https://console.cloud.google.com/')} and create (or pick) a project.
  2. {bold('APIs & Services > OAuth consent screen')}: choose External, fill in an app
     name and your email, save. Under {bold('Test users')} add your Google email
     (and anyone else who'll sign in) while the app is in Testing mode.
  3. {bold('APIs & Services > Credentials > Create credentials > OAuth client ID')},
     Application type: {bold('Web application')}.
  4. Under {bold('Authorized redirect URIs')} add exactly:""")
    for uri in redirects:
        print("       " + green(uri))
    info(f"""
  5. Create, then copy the {bold('Client ID')} and {bold('Client secret')} it shows.
     ({cyan('https://console.cloud.google.com/apis/credentials')})
""")
    if local:
        info("Locally you can skip this and use the DEV_AUTO_LOGIN shortcut instead (next step).")
    have_google = confirm("Do you have the client ID and secret now?", bool(existing.get("GOOGLE_CLIENT_ID")) or not local)
    if have_google:
        v["GOOGLE_CLIENT_ID"] = ask("Client ID", existing.get("GOOGLE_CLIENT_ID") or None, validate=v_google_id)
        v["GOOGLE_CLIENT_SECRET"] = ask("Client secret", existing.get("GOOGLE_CLIENT_SECRET") or None, secret=True)
    else:
        v["GOOGLE_CLIENT_ID"] = v["GOOGLE_CLIENT_SECRET"] = ""
        if local:
            warn("Skipping Google. Local login will use the DEV_AUTO_LOGIN shortcut.")
        else:
            warn("Without Google credentials nobody can sign in. Re-run this script when you have them.")

    if local:
        v["DEV_AUTO_LOGIN"] = "true" if confirm(
            "Auto sign-in on localhost, no Google needed? (development only)",
            existing.get("DEV_AUTO_LOGIN", "true").lower() == "true" or not have_google) else "false"
    else:
        v["DEV_AUTO_LOGIN"] = "false"

    # ---- 5. Push + secrets ---------------------------------------------------
    step(5, total, "Notifications and secrets")
    info("""
Web Push needs a contact address (sent to the push services, never shown to
users) and a key pair. I generate the key pair for you.
""")
    v["VAPID_SUBJECT"] = ask(
        "Push contact email", (existing.get("VAPID_SUBJECT", "").replace("mailto:", "")
                               if "you@example.com" not in existing.get("VAPID_SUBJECT", "") else "")
        or v.get("ADMIN_EMAIL") or None, validate=v_email)
    v["VAPID_SUBJECT"] = "mailto:" + v["VAPID_SUBJECT"]

    if VAPID_PATH.exists():
        public = vapid_public_from_pem(VAPID_PATH)
        if public:
            ok(f"Reusing existing push key ({VAPID_PATH.relative_to(ROOT)}). Keep it: replacing it "
               "would force every device to re-subscribe.")
        else:
            public = None
            warn("The existing push key file couldn't be read.")
    else:
        public = generate_vapid(VAPID_PATH)
        if public:
            ok(f"Generated push key pair at {VAPID_PATH.relative_to(ROOT)} (kept private, mode 600)")
    if not public:
        die("Couldn't create push keys: install openssl or `pip install cryptography`, then re-run.")
    v["VAPID_PUBLIC_KEY"] = public

    if existing.get("SECRET_KEY") and existing["SECRET_KEY"] != "changeme":
        v["SECRET_KEY"] = existing["SECRET_KEY"]
        ok("Keeping your existing SECRET_KEY (changing it would sign everyone out).")
    else:
        v["SECRET_KEY"] = secrets.token_hex(32)
        ok("Generated a random SECRET_KEY")

    if local:
        v["DATABASE_URL"] = "sqlite:///./data/notifaybers.db"
        v["VAPID_PRIVATE_KEY_PATH"] = "./data/vapid_private.pem"
    else:
        v["DATABASE_URL"] = "sqlite:////app/data/notifaybers.db"
        v["VAPID_PRIVATE_KEY_PATH"] = "/app/data/vapid_private.pem"

    v["SESSION_MAX_AGE_DAYS"] = existing.get("SESSION_MAX_AGE_DAYS", "30")
    v["WATCHDOG_MIN_PING_SECONDS"] = existing.get("WATCHDOG_MIN_PING_SECONDS", "60")
    v["WEBHOOK_RATE_LIMIT_PER_MINUTE"] = existing.get("WEBHOOK_RATE_LIMIT_PER_MINUTE", "30")
    if confirm("Change advanced limits? (session length, watchdog min interval, webhook rate)", False):
        v["SESSION_MAX_AGE_DAYS"] = ask("Session length in days", v["SESSION_MAX_AGE_DAYS"], validate=v_int_min(1))
        v["WATCHDOG_MIN_PING_SECONDS"] = ask(
            "Shortest allowed watchdog ping interval, seconds (min 60)", v["WATCHDOG_MIN_PING_SECONDS"],
            validate=v_int_min(60))
        v["WEBHOOK_RATE_LIMIT_PER_MINUTE"] = ask(
            "Webhook requests per minute per API key", v["WEBHOOK_RATE_LIMIT_PER_MINUTE"], validate=v_int_min(1))

    # ---- 6. Write and start --------------------------------------------------
    step(6, total, "Write .env and start")
    extras = {k: val for k, val in existing.items() if k not in MANAGED_KEYS}
    # Settings from older versions that no longer exist.
    for stale in ("ADMIN_PASSWORD", "LOGIN_MAX_ATTEMPTS", "LOGIN_WINDOW_MINUTES", "PASSWORD_LOGIN_ENABLED"):
        extras.pop(stale, None)

    if ENV_PATH.exists():
        backup = ENV_PATH.with_name(f".env.bak-{datetime.now():%Y%m%d-%H%M%S}")
        shutil.copy2(ENV_PATH, backup)
        os.chmod(backup, 0o600)
        ok(f"Backed up the old .env to {backup.name}")
    ENV_PATH.write_text(render_env(v, extras))
    os.chmod(ENV_PATH, 0o600)
    ok("Wrote .env (mode 600)")

    if local:
        start_local(v, port)
    else:
        start_server(v)


def start_local(v: dict[str, str], port: str) -> None:
    venv = ROOT / ".venv"
    py = venv / "bin" / "python"
    if confirm("Create/refresh the Python environment and install dependencies now?", True):
        if not py.exists():
            if run([sys.executable, "-m", "venv", str(venv)]) != 0:
                die("Couldn't create the virtualenv (on Debian/Ubuntu: apt install python3-venv).")
        if run([str(py), "-m", "pip", "install", "-q", "-r", "requirements.txt"]) != 0:
            die("Dependency install failed.")
        ok("Dependencies installed")
    cmd = f".venv/bin/uvicorn app.main:app --reload --port {port}"
    print()
    print(bold(green("Setup complete.")))
    info(f"""
Start the app with:

    {cmd}

Then open {v['PUBLIC_BASE_URL']}/login""" + (
        "\nYou'll be signed in automatically (DEV_AUTO_LOGIN)." if v["DEV_AUTO_LOGIN"] == "true"
        else "\nand choose Continue with Google."))
    if confirm("Start it now?", True):
        if not py.exists():
            die("No .venv yet: say yes to the dependency install, or create it first.")
        os.execv(str(venv / "bin" / "uvicorn"),
                 [str(venv / "bin" / "uvicorn"), "app.main:app", "--reload", "--port", port])


def start_server(v: dict[str, str]) -> None:
    domain = v["PUBLIC_BASE_URL"].replace("https://", "")
    started = False
    if not have_docker_compose():
        warn("Docker with the compose plugin wasn't found. Install it (https://docs.docker.com/engine/install/), "
             "then run:  docker compose up -d --build")
    elif confirm("Build and start the container now (docker compose up -d --build)?", True):
        if run(["docker", "compose", "up", "-d", "--build"]) != 0:
            die("docker compose failed. Check the output above.")
        print("  Waiting for it to answer...")
        if wait_for("http://127.0.0.1:8010/login"):
            ok("Notifaybers is running on 127.0.0.1:8010")
            started = True
        else:
            warn("It didn't answer in time. See: docker compose logs --tail 50")

    print()
    print(bold(green("Setup complete.")))
    info(f"""
Last step, point your HTTPS reverse proxy at the app (it listens on
127.0.0.1:8010). With Caddy, add to your Caddyfile and reload:

    {domain} {{
        reverse_proxy 127.0.0.1:8010
    }}

Then open {v['PUBLIC_BASE_URL']}/login, choose Continue with Google, and
sign in as {v.get('ADMIN_EMAIL') or 'your admin email'}. On iPhone, add the site to the Home
Screen first: Web Push only works from the installed app.
""" + ("" if started else "\nStart the container first (see above)."))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled. Nothing further was changed.")
        sys.exit(130)
