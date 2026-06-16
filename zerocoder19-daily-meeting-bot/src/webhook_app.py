"""Flask webhook app for PythonAnywhere deployment."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple
from zoneinfo import ZoneInfo

from flask import Flask, abort, request
import requests

from .calendar_service import (
    GoogleCalendarNotConfiguredError,
    GoogleCalendarService,
    GoogleCalendarServiceError,
)
from .config import Settings, get_settings
from .demo_calendar_service import DemoCalendarService
from .formatter import format_events_message


MAX_TELEGRAM_MESSAGE_LENGTH = 3900

app = Flask(__name__)


HELP_TEXT = """Zerocoder19 Daily Meeting Bot

Команды:
/start - приветствие
/help - справка
/health - статус webhook
/today - встречи на сегодня
/tomorrow - встречи на завтра
"""


@app.route("/", methods=["GET"])
def index() -> str:
    return "Zerocoder19 Daily Meeting Bot webhook is alive"


@app.route("/<secret>", methods=["POST"])
def telegram_webhook(secret: str) -> Tuple[str, int]:
    settings = get_settings()
    if not settings.webhook_secret or secret != settings.webhook_secret:
        print("Webhook rejected: invalid secret")
        abort(403)

    update = request.get_json(silent=True) or {}
    try:
        chat_id = _extract_chat_id(update)
        command = _extract_command(update)
        if chat_id is None:
            print("Webhook update ignored: chat_id not found")
            return "ok", 200

        response_text = _handle_command(command, settings)
        _send_telegram_message(settings.telegram_bot_token, chat_id, response_text)
    except Exception as error:
        print(f"Webhook error: {error}")
        if "chat_id" in locals() and chat_id is not None:
            _send_telegram_message(
                settings.telegram_bot_token,
                chat_id,
                "Произошла ошибка при обработке команды. Проверьте логи webhook.",
            )

    return "ok", 200


def _extract_chat_id(update: Dict[str, Any]) -> Any:
    message = update.get("message") or update.get("edited_message") or {}
    chat = message.get("chat") or {}
    return chat.get("id")


def _extract_command(update: Dict[str, Any]) -> str:
    message = update.get("message") or update.get("edited_message") or {}
    text = str(message.get("text") or "").strip()
    return text.split()[0].split("@")[0].lower() if text else ""


def _handle_command(command: str, settings: Settings) -> str:
    if command in {"", "/start"}:
        return (
            "Привет! Я показываю встречи на сегодня и завтра и отмечаю, "
            "есть ли в событиях Zoom-ссылки.\n\n"
            + HELP_TEXT
        )

    if command == "/help":
        return HELP_TEXT

    if command == "/health":
        return "✅ Бот работает через PythonAnywhere webhook"

    if command == "/today":
        today = datetime.now(ZoneInfo(settings.timezone)).date()
        return _format_events_for_date(settings, today, f"Сегодня, {today:%d.%m.%Y}")

    if command == "/tomorrow":
        tomorrow = datetime.now(ZoneInfo(settings.timezone)).date() + timedelta(days=1)
        return _format_events_for_date(
            settings,
            tomorrow,
            f"Завтра, {tomorrow:%d.%m.%Y}",
        )

    return "Неизвестная команда. Используйте /help."


def _format_events_for_date(settings: Settings, target_date: Any, label: str) -> str:
    service = _build_calendar_service(settings)
    checked_calendar_count = 1 if settings.use_demo_mode else len(settings.google_calendar_ids)

    try:
        events = service.get_events_for_date(target_date)
    except GoogleCalendarNotConfiguredError as error:
        return str(error)
    except GoogleCalendarServiceError as error:
        print(f"Google Calendar error: {error}")
        return str(error)

    return format_events_message(
        events,
        label,
        checked_calendar_count=checked_calendar_count,
    )


def _build_calendar_service(settings: Settings) -> Any:
    if settings.use_demo_mode:
        return DemoCalendarService(timezone=settings.timezone)

    return GoogleCalendarService(
        calendar_ids=settings.google_calendar_ids,
        timezone=settings.timezone,
    )


def _send_telegram_message(token: str, chat_id: Any, text: str) -> None:
    if not token:
        print("Telegram token is empty; message was not sent.")
        return

    for chunk in _split_message(text, MAX_TELEGRAM_MESSAGE_LENGTH):
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
        if not response.ok:
            print(
                "Telegram sendMessage failed: "
                f"status={response.status_code} body={response.text}"
            )


def _split_message(text: str, limit: int) -> List[str]:
    if len(text) <= limit:
        return [text]

    chunks: List[str] = []
    current = ""
    for line in text.splitlines(keepends=True):
        if len(current) + len(line) > limit:
            if current:
                chunks.append(current)
                current = ""
            while len(line) > limit:
                chunks.append(line[:limit])
                line = line[limit:]
        current += line

    if current:
        chunks.append(current)

    return chunks
