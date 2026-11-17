from pathlib import Path

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")

_STATIC_DIR = Path("app/static")


def asset_v(name: str) -> str:
    """Cache-busting token for a static file (its mtime), so browsers and iOS
    home-screen apps refetch CSS/JS after a deploy instead of using a stale copy."""
    try:
        return str(int((_STATIC_DIR / name).stat().st_mtime))
    except OSError:
        return "0"


templates.env.globals["asset_v"] = asset_v
