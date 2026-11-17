import json
import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from sqlmodel import Session, select

from app.db import engine
from app.models import Reminder, User, Watchdog
from app.push import notify_user
from app.reminders import compute_next_run

logger = logging.getLogger("notifaybers.scheduler")

scheduler = BackgroundScheduler()


def check_reminders() -> None:
    with Session(engine) as session:
        due = session.exec(
            select(Reminder).where(
                Reminder.enabled == True,  # noqa: E712
                Reminder.next_run_at <= datetime.utcnow(),
            )
        ).all()

        for reminder in due:
            user = session.get(User, reminder.user_id)
            if user is None:
                continue
            try:
                notify_user(
                    session,
                    user,
                    title=reminder.title,
                    body=reminder.body,
                    url=reminder.url,
                    source="reminder",
                )
            except Exception:
                logger.exception("failed to send reminder %s", reminder.id)

            if reminder.schedule_type == "once":
                reminder.enabled = False
                reminder.next_run_at = None
            else:
                value = json.loads(reminder.schedule_value)
                reminder.next_run_at = compute_next_run(
                    reminder.schedule_type, value, user.timezone, after=datetime.utcnow()
                )
            session.add(reminder)
            session.commit()


def check_watchdogs() -> None:
    now = datetime.utcnow()
    with Session(engine) as session:
        watchdogs = session.exec(
            select(Watchdog).where(
                Watchdog.enabled == True,  # noqa: E712
            )
        ).all()

        for wd in watchdogs:
            user = session.get(User, wd.user_id)
            if user is None:
                continue

            threshold = wd.ping_interval_seconds + wd.grace_period_seconds
            is_missed = False
            last_seen_str = ""

            if wd.last_ping_at is not None:
                elapsed = (now - wd.last_ping_at).total_seconds()
                if elapsed > threshold:
                    is_missed = True
                    mins = int(elapsed // 60)
                    last_seen_str = f"Last ping was {mins}m ago."
            elif wd.status == "pending":
                elapsed = (now - wd.created_at).total_seconds()
                if elapsed > threshold:
                    is_missed = True
                    last_seen_str = "No ping has ever been received."

            if is_missed and not wd.alert_sent:
                wd.status = "down"
                wd.alert_sent = True
                session.add(wd)
                session.commit()

                try:
                    notify_user(
                        session,
                        user,
                        title=f"⚠️ Watchdog Down: {wd.name}",
                        body=f"Expected ping every {wd.ping_interval_seconds}s. {last_seen_str}",
                        url="/watchdogs",
                        source="watchdog",
                    )
                except Exception:
                    logger.exception("Failed to send alert for watchdog %s", wd.id)


def start_scheduler() -> None:
    scheduler.add_job(check_reminders, "interval", seconds=60, id="check_reminders")
    scheduler.add_job(check_watchdogs, "interval", seconds=30, id="check_watchdogs")
    scheduler.start()
