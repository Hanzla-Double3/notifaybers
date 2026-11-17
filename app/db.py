import secrets

from sqlalchemy import or_
from sqlmodel import Session, SQLModel, create_engine, select

from app.config import settings
from app.models import User, Watchdog
from app.security import hash_password

connect_args = {"check_same_thread": False}
engine = create_engine(settings.database_url, connect_args=connect_args)


def _migrate() -> None:
    # SQLModel.metadata.create_all only creates missing tables, never adds
    # columns to existing ones -- so new nullable columns need a manual,
    # additive ALTER TABLE here. Safe on SQLite: existing rows just get NULL.
    with engine.connect() as conn:
        reminder_cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(reminder)").fetchall()}
        if "category" not in reminder_cols:
            conn.exec_driver_sql("ALTER TABLE reminder ADD COLUMN category TEXT")
            conn.commit()

        user_cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(user)").fetchall()}
        if "watchdogs_enabled" not in user_cols:
            conn.exec_driver_sql("ALTER TABLE user ADD COLUMN watchdogs_enabled BOOLEAN NOT NULL DEFAULT 0")
            # Off by default, but don't hide the feature from anyone who already uses it.
            conn.exec_driver_sql(
                "UPDATE user SET watchdogs_enabled = 1 WHERE id IN (SELECT DISTINCT user_id FROM watchdog)"
            )
            conn.commit()
        if "reminders_enabled" not in user_cols:
            # On for everyone who already has the app: switching a feature off is opt-in.
            conn.exec_driver_sql("ALTER TABLE user ADD COLUMN reminders_enabled BOOLEAN NOT NULL DEFAULT 1")
            conn.commit()
        if "bills_enabled" not in user_cols:
            conn.exec_driver_sql("ALTER TABLE user ADD COLUMN bills_enabled BOOLEAN NOT NULL DEFAULT 0")
            conn.commit()
        if "is_admin" not in user_cols:
            conn.exec_driver_sql("ALTER TABLE user ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0")
            conn.commit()
        if "last_active_at" not in user_cols:
            conn.exec_driver_sql("ALTER TABLE user ADD COLUMN last_active_at DATETIME")
            conn.commit()
        if "bills_language" not in user_cols:
            conn.exec_driver_sql("ALTER TABLE user ADD COLUMN bills_language TEXT NOT NULL DEFAULT 'ur_roman'")
            conn.commit()
        for col in ("email", "google_sub", "name"):
            if col not in user_cols:
                conn.exec_driver_sql(f"ALTER TABLE user ADD COLUMN {col} TEXT")
                conn.commit()
        # Unique indexes (NULLs are allowed to repeat in SQLite). Names match what
        # SQLModel generates for fresh databases.
        conn.exec_driver_sql("CREATE UNIQUE INDEX IF NOT EXISTS ix_user_email ON user (email)")
        conn.exec_driver_sql("CREATE UNIQUE INDEX IF NOT EXISTS ix_user_google_sub ON user (google_sub)")
        conn.commit()
        if "openai_api_key" not in user_cols:
            conn.exec_driver_sql("ALTER TABLE user ADD COLUMN openai_api_key TEXT")
            conn.commit()
        if "openai_base_url" not in user_cols:
            conn.exec_driver_sql("ALTER TABLE user ADD COLUMN openai_base_url TEXT DEFAULT 'https://api.openai.com/v1'")
            conn.commit()
        if "openai_model" not in user_cols:
            conn.exec_driver_sql("ALTER TABLE user ADD COLUMN openai_model TEXT DEFAULT 'gpt-4o-mini'")
            conn.commit()


def init_db() -> None:
    SQLModel.metadata.create_all(engine)  # also creates the bill tables
    _migrate()
    with Session(engine) as session:
        existing = session.exec(
            select(User).where(User.username == settings.admin_username)
        ).first()
        if existing is None:
            user = User(
                username=settings.admin_username,
                password_hash=hash_password(settings.admin_password or secrets.token_urlsafe(32)),
                timezone=settings.default_timezone,
            )
            session.add(user)
            session.commit()
        # The configured admin account is always an admin. This only ever promotes:
        # nobody is demoted behind your back if the env values change later.
        promote_configured_admin(session)


def promote_configured_admin(session: Session, user: User | None = None) -> None:
    """Make the configured admin account an admin: the seeded ADMIN_USERNAME account and
    whichever account has the ADMIN_EMAIL address (they are the same account once linked)."""
    if user is not None:
        admin_email = settings.admin_email.strip().lower()
        is_configured = user.username == settings.admin_username or bool(
            admin_email and (user.email or "").lower() == admin_email
        )
        if is_configured and not user.is_admin:
            user.is_admin = True
            session.add(user)
            session.commit()
        return
    candidates = [User.username == settings.admin_username]
    if settings.admin_email.strip():
        candidates.append(User.email == settings.admin_email.strip().lower())
    for match in session.exec(select(User).where(or_(*candidates))).all():
        promote_configured_admin(session, match)


def get_session():
    with Session(engine) as session:
        yield session
