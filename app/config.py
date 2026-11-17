from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    secret_key: str
    admin_username: str
    admin_password: str = ""  # legacy; accounts sign in with Google now
    default_timezone: str = "UTC"

    database_url: str = "sqlite:///./data/notifaybers.db"
    # Held by whichever app copy runs the scheduler (see app/scheduler.py).
    scheduler_lock_path: str = "./data/scheduler.lock"
    # Label for this copy ("blue"/"green"), reported by /healthz. Set by the deploy script.
    deploy_slot: str = ""

    vapid_public_key: str = ""
    vapid_private_key_path: str = "./data/vapid_private.pem"
    vapid_subject: str = "mailto:admin@example.com"

    session_max_age_days: int = 30
    session_secure_cookie: bool = True

    # Google sign-in. Enabled when both client id and secret are set.
    google_client_id: str = ""
    google_client_secret: str = ""
    # Google email of the existing admin account; links it on first Google sign-in
    # so its reminders, keys and devices carry over.
    admin_email: str = ""
    # Comma-separated Google emails allowed to sign in (admin_email is always allowed).
    allowed_emails: str = ""
    # Let any verified Google account sign up. Off by default: allowlist only.
    open_signup: bool = False
    # LOCAL DEBUGGING ONLY: visiting /login over a direct loopback connection signs
    # you in as the seeded admin, no Google needed. Ignored for proxied requests.
    dev_auto_login: bool = False

    login_max_attempts: int = 3
    login_window_minutes: int = 60

    webhook_rate_limit_per_minute: int = 30

    # Public origin of this deployment, e.g. https://notify.example.com. Shown in
    # webhook/ping snippets. Falls back to the request's own origin when empty.
    public_base_url: str = ""

    # Admin-controlled floor for watchdog ping intervals (not user-editable).
    watchdog_min_ping_seconds: int = Field(default=60, ge=60)

    @property
    def google_enabled(self) -> bool:
        return bool(self.google_client_id.strip() and self.google_client_secret.strip())

    @property
    def allowed_email_set(self) -> set[str]:
        emails = {e.strip().lower() for e in self.allowed_emails.split(",") if e.strip()}
        if self.admin_email.strip():
            emails.add(self.admin_email.strip().lower())
        return emails


settings = Settings()
