import json
import logging
import secrets
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import requests
from sqlmodel import Session, select

from app.config import settings
from app.models import Reminder, User, Watchdog
from app.push import notify_user
from app.reminders import compute_next_run, validate_schedule

logger = logging.getLogger("notifaybers.ai")

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "create_reminder",
            "description": "Create a new scheduled reminder for the user. Supports one-off datetimes, cron expressions (e.g. '0 9 * * 1-5' for 9 AM weekdays), or recurring interval minutes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Short, clear title of the reminder"},
                    "schedule_type": {
                        "type": "string",
                        "enum": ["once", "cron", "interval"],
                        "description": "Type of schedule: 'once' for a specific date & time, 'cron' for standard cron expression, 'interval' for recurring every N minutes.",
                    },
                    "schedule_value": {
                        "type": "string",
                        "description": "For 'once': local ISO datetime like '2026-09-26T14:30' (never include timezone offset or Z). For 'cron': standard 5-part cron syntax like '0 9 * * 1-5'. For 'interval': number of minutes as integer string like '60' -- only exact divisors of 60 (minutes) or 24 (hours) are supported since this is translated to a cron expression; anything else, use 'cron' directly.",
                    },
                    "category": {
                        "type": "string",
                        "description": "Short, freeform category tag for grouping the reminder (any label the user wants, e.g. 'work', 'gym', 'bills')",
                    },
                    "body": {"type": "string", "description": "Optional notes or extra details"},
                    "url": {"type": "string", "description": "Optional destination URL when clicked"},
                },
                "required": ["title", "schedule_type", "schedule_value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_reminders",
            "description": "List existing reminders for the user, most recently created first",
            "parameters": {
                "type": "object",
                "properties": {
                    "enabled_only": {
                        "type": "boolean",
                        "description": "Whether to only return active enabled reminders (default true)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max number of reminders to return (default 20, capped at 50). Keep this small -- results are dumped into the conversation.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_reminder",
            "description": "Delete a reminder by its ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "reminder_id": {"type": "integer", "description": "Numeric ID of the reminder"}
                },
                "required": ["reminder_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_watchdog",
            "description": "Create a new watchdog / heartbeat monitor. Returns a ping URL to curl from a script, server, or cron job.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name of the service or job (e.g. 'Postgres Backup', 'Disk Health')"},
                    "ping_interval_seconds": {
                        "type": "integer",
                        "description": "Expected interval between pings in seconds. Minimum is set by the server administrator (e.g. 86400 for 24h, 3600 for 1h, 300 for 5m).",
                    },
                    "grace_period_seconds": {
                        "type": "integer",
                        "description": "Grace period in seconds before alerting when missed (default 300 / 5 minutes)",
                    },
                },
                "required": ["name", "ping_interval_seconds"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_watchdogs",
            "description": "List existing watchdogs and their health status, most recently created first",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Max number of watchdogs to return (default 20, capped at 50). Keep this small -- results are dumped into the conversation.",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_notification",
            "description": "Send an immediate push notification alert to the user's phone/devices right now",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Title of the alert"},
                    "body": {"type": "string", "description": "Body message text"},
                    "url": {"type": "string", "description": "Optional link URL"},
                },
                "required": ["title"],
            },
        },
    },
]


WATCHDOG_TOOLS = {"create_watchdog", "list_watchdogs"}


def _clamp_limit(value: Any, default: int = 20, cap: int = 50) -> int:
    try:
        n = int(value) if value is not None else default
    except (TypeError, ValueError):
        n = default
    return max(1, min(n, cap))


def _minutes_to_cron(minutes: int) -> str:
    """Translates a plain 'every N minutes' interval into a cron expression.

    Cron can't express arbitrary intervals -- only ones that tile evenly
    into an hour or a day -- so this covers the common cases and raises
    for anything else, asking the caller to use 'cron' directly instead.
    """
    if minutes <= 0:
        raise ValueError("interval minutes must be positive")
    if minutes < 60:
        if 60 % minutes != 0:
            raise ValueError(
                f"{minutes} minutes doesn't divide evenly into an hour; use schedule_type='cron' instead"
            )
        return f"*/{minutes} * * * *"
    if minutes % 60 == 0:
        hours = minutes // 60
        if hours < 24 and 24 % hours == 0:
            return f"0 */{hours} * * *"
        if hours == 24:
            return "0 0 * * *"
    raise ValueError(
        f"{minutes} minutes doesn't tile evenly into a day; use schedule_type='cron' instead"
    )


def execute_tool(
    name: str, args: dict[str, Any], user: User, session: Session, domain: str = ""
) -> dict[str, Any]:
    """Executes a tool call locally against the SQLite database on behalf of user."""
    if name == "create_reminder":
        title = args.get("title", "").strip()
        schedule_type = args.get("schedule_type", "once")
        raw_val = args.get("schedule_value", "")
        category = args.get("category")
        body = args.get("body")
        url = args.get("url")

        if not title:
            return {"error": "Title cannot be empty"}

        if schedule_type == "once":
            parsed_val = {"datetime": raw_val}
        elif schedule_type == "cron":
            parsed_val = {"expr": raw_val}
        elif schedule_type == "interval":
            try:
                cron_expr = _minutes_to_cron(int(raw_val))
            except (TypeError, ValueError) as exc:
                return {"error": f"Invalid interval: {exc}"}
            schedule_type = "cron"
            parsed_val = {"expr": cron_expr}
        else:
            return {"error": f"Unsupported schedule_type: {schedule_type}"}

        try:
            validate_schedule(schedule_type, parsed_val)
        except ValueError as exc:
            return {"error": f"Invalid schedule value: {exc}"}

        next_run_at = compute_next_run(schedule_type, parsed_val, user.timezone)

        reminder = Reminder(
            user_id=user.id,
            title=title,
            body=body,
            url=url,
            category=category,
            schedule_type=schedule_type,
            schedule_value=json.dumps(parsed_val),
            enabled=next_run_at is not None,
            next_run_at=next_run_at,
        )
        session.add(reminder)
        session.commit()
        session.refresh(reminder)

        return {
            "status": "created",
            "id": reminder.id,
            "title": reminder.title,
            "schedule_type": reminder.schedule_type,
            "category": reminder.category,
            "next_run_at": reminder.next_run_at.isoformat() if reminder.next_run_at else None,
        }

    elif name == "list_reminders":
        enabled_only = args.get("enabled_only", True)
        limit = _clamp_limit(args.get("limit"))
        query = select(Reminder).where(Reminder.user_id == user.id)
        if enabled_only:
            query = query.where(Reminder.enabled == True)  # noqa: E712
        reminders = session.exec(query.order_by(Reminder.created_at.desc()).limit(limit)).all()
        return {
            "reminders": [
                {
                    "id": r.id,
                    "title": r.title,
                    "schedule_type": r.schedule_type,
                    "category": r.category,
                    "next_run_at": r.next_run_at.isoformat() if r.next_run_at else None,
                    "enabled": r.enabled,
                }
                for r in reminders
            ]
        }

    elif name == "delete_reminder":
        reminder_id = args.get("reminder_id")
        reminder = session.get(Reminder, reminder_id)
        if not reminder or reminder.user_id != user.id:
            return {"error": f"Reminder {reminder_id} not found"}
        title = reminder.title
        session.delete(reminder)
        session.commit()
        return {"status": "deleted", "id": reminder_id, "title": title}

    elif name in WATCHDOG_TOOLS and not user.watchdogs_enabled:
        return {"error": "Watchdogs are disabled. The user can enable them in Settings > Features."}

    elif name == "create_watchdog":
        name_str = args.get("name", "").strip()
        interval = int(args.get("ping_interval_seconds", 86400))
        grace = int(args.get("grace_period_seconds", 300))

        if not name_str:
            return {"error": "Watchdog name is required"}

        min_allowed = settings.watchdog_min_ping_seconds
        if interval < min_allowed:
            return {"error": f"Ping interval must be at least {min_allowed} seconds"}

        token = secrets.token_urlsafe(16)
        wd = Watchdog(
            user_id=user.id,
            name=name_str,
            token=token,
            ping_interval_seconds=interval,
            grace_period_seconds=grace,
            status="pending",
            enabled=True,
        )
        session.add(wd)
        session.commit()
        session.refresh(wd)

        ping_url = f"{domain}/api/ping/{wd.token}" if domain else f"/api/ping/{wd.token}"
        return {
            "status": "created",
            "id": wd.id,
            "name": wd.name,
            "token": wd.token,
            "ping_url": ping_url,
            "ping_interval_seconds": wd.ping_interval_seconds,
        }

    elif name == "list_watchdogs":
        limit = _clamp_limit(args.get("limit"))
        wds = session.exec(
            select(Watchdog)
            .where(Watchdog.user_id == user.id)
            .order_by(Watchdog.created_at.desc())
            .limit(limit)
        ).all()
        return {
            "watchdogs": [
                {
                    "id": w.id,
                    "name": w.name,
                    "token": w.token,
                    "status": w.status,
                    "ping_interval_seconds": w.ping_interval_seconds,
                    "last_ping_at": w.last_ping_at.isoformat() if w.last_ping_at else None,
                    "enabled": w.enabled,
                }
                for w in wds
            ]
        }

    elif name == "send_notification":
        title = args.get("title", "Alert")
        body = args.get("body")
        url = args.get("url")
        status = notify_user(session, user, title=title, body=body, url=url, source="ai_assistant")
        return {"status": status, "title": title}

    return {"error": f"Unknown tool: {name}"}


def chat_with_llm(
    user: User, session: Session, messages: list[dict[str, Any]], domain: str = ""
) -> dict[str, Any]:
    """Performs an OpenAI-compatible chat completion with MCP tool calls."""
    if not user.openai_api_key or not user.openai_api_key.strip():
        raise ValueError(
            "OpenAI API Key is not configured. Please add your API key in Settings -> AI Assistant."
        )

    base_url = (user.openai_base_url or "https://api.openai.com/v1").rstrip("/")
    model = user.openai_model or "gpt-4o-mini"
    tz_str = user.timezone or "UTC"

    try:
        now_tz = datetime.now(ZoneInfo(tz_str))
    except Exception:
        now_tz = datetime.utcnow()

    now_iso = now_tz.strftime("%Y-%m-%d %H:%M:%S (%A)")
    watchdogs_on = bool(user.watchdogs_enabled)
    tools = (
        TOOLS_SCHEMA
        if watchdogs_on
        else [t for t in TOOLS_SCHEMA if t["function"]["name"] not in WATCHDOG_TOOLS]
    )
    watchdog_ctx = (
        f"- Minimum watchdog ping interval: {settings.watchdog_min_ping_seconds} seconds"
        if watchdogs_on
        else "- The Watchdogs feature is disabled for this user"
    )

    system_prompt = (
        f"You are Notifaybers AI Assistant, an intelligent, helpful personal notification and reminder assistant.\n"
        f"- Current user time: {now_iso}\n"
        f"- User timezone: {tz_str}\n"
        f"{watchdog_ctx}\n\n"
        "Guidelines:\n"
        "1. When the user asks to set, schedule, or create a reminder, ALWAYS call the `create_reminder` tool with appropriate parameters.\n"
        "   - For specific times (e.g. 'tomorrow at 9am', 'in 30 minutes'), calculate the exact ISO datetime 'YYYY-MM-DDTHH:MM' relative to the user's current time and use schedule_type='once'. Do NOT add timezone offset or 'Z' to schedule_value.\n"
        "   - For recurring schedules (e.g. 'every weekday at 10am', 'every Sunday at 8pm'), generate standard 5-part cron syntax and use schedule_type='cron'.\n"
        "   - For simple recurring intervals (e.g. 'every 2 hours', 'every 15 minutes'), use schedule_type='interval' and value in minutes -- only works for minute counts that divide evenly into 60, or hour counts that divide evenly into 24. For anything else (e.g. 'every 7 minutes', 'every 5 hours'), use schedule_type='cron' instead.\n"
        "   - Category is freeform -- pick any short, sensible label based on what the reminder is about (e.g. 'work', 'gym', 'bills', 'birthdays'); there is no fixed list.\n"
        "2. When user asks to monitor a script or cron job or create a watchdog, call `create_watchdog`.\n"
        "3. When user asks to list reminders or watchdogs, call `list_reminders` or `list_watchdogs`.\n"
        "4. Be concise, friendly, and confirm the exact details of actions taken.\n"
        "5. Do not use emojis anywhere in your replies."
    )
    if not watchdogs_on:
        system_prompt += (
            "\n6. Watchdogs are disabled for this user. If they ask for one, tell them to enable "
            "Watchdogs in Settings > Features first."
        )

    conv: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}] + messages
    executed_tools: list[dict[str, Any]] = []

    headers = {
        "Authorization": f"Bearer {user.openai_api_key.strip()}",
        "Content-Type": "application/json",
    }

    # Tool calling loop (up to 3 turns)
    for _ in range(3):
        payload = {
            "model": model,
            "messages": conv,
            "tools": tools,
            "tool_choice": "auto",
            "temperature": 0.3,
        }

        try:
            resp = requests.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.HTTPError as err:
            err_msg = err.response.text if err.response is not None else str(err)
            logger.error("LLM API error: %s", err_msg)
            try:
                err_json = json.loads(err_msg)
                detail = err_json.get("error", {}).get("message", err_msg)
            except Exception:
                detail = err_msg
            raise ValueError(f"AI Provider error: {detail}")
        except Exception as exc:
            logger.exception("Failed to call LLM API: %s", exc)
            raise ValueError(f"Failed to connect to AI provider: {exc}")

        choices = data.get("choices", [])
        if not choices:
            raise ValueError("No response received from AI model")

        msg = choices[0].get("message", {})
        tool_calls = msg.get("tool_calls")

        if not tool_calls:
            # Final reply message reached
            return {
                "reply": msg.get("content", ""),
                "executed_tools": executed_tools,
            }

        # Append assistant message with tool calls
        conv.append(msg)

        for tc in tool_calls:
            func = tc.get("function", {})
            f_name = func.get("name", "")
            try:
                f_args = json.loads(func.get("arguments", "{}"))
            except Exception:
                f_args = {}

            tool_res = execute_tool(f_name, f_args, user, session, domain=domain)
            executed_tools.append({"name": f_name, "args": f_args, "result": tool_res})

            conv.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.get("id"),
                    "name": f_name,
                    "content": json.dumps(tool_res),
                }
            )

    return {
        "reply": "Action completed successfully.",
        "executed_tools": executed_tools,
    }


def get_mcp_manifest() -> dict[str, Any]:
    """Returns tools formatted as Model Context Protocol (MCP) tool definitions."""
    mcp_tools = []
    for t in TOOLS_SCHEMA:
        fn = t["function"]
        mcp_tools.append(
            {
                "name": fn["name"],
                "description": fn["description"],
                "inputSchema": fn["parameters"],
            }
        )
    return {
        "name": "notifaybers",
        "description": "Notifaybers personal notification hub and reminder scheduler MCP server",
        "tools": mcp_tools,
    }
