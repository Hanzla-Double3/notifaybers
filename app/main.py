from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.db import init_db
from app.routes import api, auth, pages, webhook
from app.scheduler import start_scheduler

app = FastAPI(title="Notifaybers")

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie="notifaybers_session",
    max_age=settings.session_max_age_days * 24 * 60 * 60,
    same_site="lax",
    https_only=settings.session_secure_cookie,
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/healthz")
def healthz():
    """Liveness for deploys: the database answers; reports which copy and whether it runs the scheduler."""
    from sqlmodel import Session, text

    from app.db import engine
    from app.scheduler import scheduler
    from app.version import app_version

    with Session(engine) as session:
        session.exec(text("SELECT 1"))
    return {"status": "ok", "slot": settings.deploy_slot, "scheduler": scheduler.running, "version": app_version()}


@app.get("/sw.js")
def service_worker():
    # Served from the root (not /static/) so its default scope covers the
    # whole app -- registering it from under /static/ would scope it to
    # /static/ only, and navigator.serviceWorker.ready would never resolve
    # for pages like / or /login.
    return FileResponse("app/static/sw.js", media_type="application/javascript")


@app.get("/favicon.ico")
def favicon():
    return FileResponse("app/static/icons/favicon.ico", media_type="image/x-icon")


@app.get("/manifest.json")
def manifest():
    return FileResponse("app/static/manifest.json", media_type="application/manifest+json")


app.include_router(auth.router)
app.include_router(pages.router)
app.include_router(api.router)
app.include_router(webhook.router)


@app.on_event("startup")
def on_startup():
    init_db()
    start_scheduler()
