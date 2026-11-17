"""The running version: a short commit id (plus date) shown in Settings.

Deploys write a VERSION file into the build (git history is not in the image);
a local checkout falls back to asking git; anything else is "dev".
"""
import subprocess
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@lru_cache(maxsize=1)
def app_version() -> str:
    try:
        text = (ROOT / "VERSION").read_text().strip()
        if text:
            return text
    except OSError:
        pass
    try:
        out = subprocess.run(
            ["git", "-C", str(ROOT), "log", "-1", "--format=%h · %cs"],
            capture_output=True, text=True, timeout=3,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return "dev"
