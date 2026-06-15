"""Telegram entry point for Zerocoder19 Daily Meeting Bot."""

from datetime import date, datetime, timedelta
from html import escape
import logging
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, ApplicationBuilder, CommandHandler, ContextTypes

from .calendar_service import (
    CalendarService,
    GoogleCalendarNotConfiguredError,
    GoogleCalendarService,
    GoogleCalendarServiceError,
)
from .config import Settings, get_settings
from .demo_calendar_service import DemoCalendarService
from .formatter import format_events_message


logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
LOGGER = logging.getLogger(__name__)

HELP_TEXT = """<b>Zerocoder19 Daily Meeting Bot</b>

Команды:
/today - встречи на сегодня
/tomorrow - встречи на завтра
/demo - показать возможности демо-режима
/caldebug - диагностика календаря на сегодня
/calendars - список календарей Google аккаунта
/health - проверить состояние бота
/help - показать справку
"""


def _service(context: ContextTypes.DEFAULT_TYPE) -> CalendarService:
    return context.application.bot_data["calendar_service"]


def _demo_service(context: ContextTypes.DEFAULT_TYPE) -> DemoCalendarService:
    return context.application.bot_data["demo_calendar_service"]


def _settings(context: ContextTypes.DEFAULT_TYPE) -> Settings:
    return context.application.bot_data["settings"]


async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    await update.effective_message.reply_text(
        "Привет! Я показываю встречи на сегодня и завтра и отмечаю, "
        "есть ли в событиях Zoom-ссылки.\n\n" + HELP_TEXT,
        parse_mode=ParseMode.HTML,
    )


async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    await update.effective_message.reply_text(HELP_TEXT, parse_mode=ParseMode.HTML)


async def health_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    settings = _settings(context)
    mode = "демо" if settings.use_demo_mode else "Google Calendar"
    await update.effective_message.reply_text(
        "Статус: работает ✅\n"
        f"Режим: {mode}\n"
        f"Часовой пояс: {settings.timezone}"
    )


async def demo_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    events = _demo_service(context).get_today_events()
    message = (
        "Демо-режим использует обезличенные события из "
        "<code>data/sample_events.json</code>.\n\n"
        + format_events_message(events, "Демо: сегодня")
    )
    await update.effective_message.reply_text(message, parse_mode=ParseMode.HTML)


async def today_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    settings = _settings(context)
    today = datetime.now(ZoneInfo(settings.timezone)).date()
    await _send_events_message(
        update,
        context,
        today,
        f"Сегодня, {today:%d.%m.%Y}",
    )


async def tomorrow_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    settings = _settings(context)
    tomorrow = datetime.now(ZoneInfo(settings.timezone)).date() + timedelta(days=1)
    await _send_events_message(
        update,
        context,
        tomorrow,
        f"Завтра, {tomorrow:%d.%m.%Y}",
    )


async def caldebug_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    settings = _settings(context)
    today = datetime.now(ZoneInfo(settings.timezone)).date()

    try:
        debug_info = _get_calendar_debug_info(context, today)
    except GoogleCalendarNotConfiguredError as error:
        await update.effective_message.reply_text(str(error))
        return
    except GoogleCalendarServiceError as error:
        LOGGER.exception("Google Calendar debug request failed.")
        await update.effective_message.reply_text(str(error))
        return

    titles = debug_info["event_titles"][:10]
    if titles:
        title_lines = "\n".join(
            f"{index}. {escape(str(title))}"
            for index, title in enumerate(titles, start=1)
        )
    else:
        title_lines = "Нет событий."

    message = (
        "<b>Calendar debug</b>\n"
        f"USE_DEMO_MODE: {settings.use_demo_mode}\n"
        f"TIMEZONE: {escape(settings.timezone)}\n"
        "calendar_ids:\n"
        f"{_format_calendar_ids(debug_info['calendar_ids'])}\n"
        f"timeMin today: {escape(str(debug_info['time_min']))}\n"
        f"timeMax today: {escape(str(debug_info['time_max']))}\n"
        f"Проверено календарей: {debug_info['checked_calendar_count']}\n"
        f"Общее количество событий: {debug_info['event_count']}\n\n"
        "<b>Событий по календарям:</b>\n"
        f"{_format_events_by_calendar(debug_info['events_by_calendar'])}\n\n"
        "<b>Ошибки календарей:</b>\n"
        f"{_format_calendar_errors(debug_info['calendar_errors'])}\n\n"
        "<b>Первые 10 событий:</b>\n"
        f"{title_lines}"
    )
    await update.effective_message.reply_text(
        message,
        parse_mode=ParseMode.HTML,
    )


async def calendars_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    settings = _settings(context)
    service = _service(context)

    if settings.use_demo_mode or not hasattr(service, "list_calendars"):
        await update.effective_message.reply_text(
            "Команда /calendars доступна в Google Calendar режиме. "
            "Установите USE_DEMO_MODE=false."
        )
        return

    try:
        calendars = service.list_calendars()  # type: ignore[attr-defined]
    except GoogleCalendarNotConfiguredError as error:
        await update.effective_message.reply_text(str(error))
        return
    except GoogleCalendarServiceError as error:
        LOGGER.exception("Google Calendar list request failed.")
        await update.effective_message.reply_text(str(error))
        return

    if not calendars:
        await update.effective_message.reply_text("Календари не найдены.")
        return

    lines = ["<b>Google Calendars</b>", f"Найдено календарей: {len(calendars)}"]
    for index, calendar in enumerate(calendars, start=1):
        summary = escape(str(calendar.get("summary") or "Без названия"))
        calendar_id = escape(str(calendar.get("id") or ""))
        primary = "true" if calendar.get("primary", False) else "false"
        access_role = escape(str(calendar.get("accessRole") or ""))

        lines.extend(
            [
                "",
                f"<b>{index}. {summary}</b>",
                f"id: <code>{calendar_id}</code>",
                f"primary: {primary}",
                f"accessRole: {access_role}",
            ]
        )

    await update.effective_message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.HTML,
    )


def _get_calendar_debug_info(
    context: ContextTypes.DEFAULT_TYPE,
    target_date: date,
) -> Dict[str, Any]:
    settings = _settings(context)
    service = _service(context)

    if hasattr(service, "get_debug_info_for_date"):
        return service.get_debug_info_for_date(target_date)  # type: ignore[attr-defined]

    local_start = datetime.combine(
        target_date,
        datetime.min.time(),
        tzinfo=ZoneInfo(settings.timezone),
    )
    local_end = local_start + timedelta(days=1)
    events = service.get_events_for_date(target_date)
    event_titles: List[str] = [
        str(event.get("title", "Без названия"))
        for event in events
    ]

    return {
        "calendar_ids": settings.google_calendar_ids,
        "time_min": local_start.isoformat(),
        "time_max": local_end.isoformat(),
        "checked_calendar_count": 1,
        "events_by_calendar": {"demo": len(events)},
        "calendar_errors": {},
        "event_count": len(events),
        "event_titles": event_titles,
    }


def _format_calendar_ids(calendar_ids: List[str]) -> str:
    return "\n".join(
        f"- <code>{escape(str(calendar_id))}</code>"
        for calendar_id in calendar_ids
    ) or "- нет календарей"


def _format_events_by_calendar(events_by_calendar: Dict[str, int]) -> str:
    if not events_by_calendar:
        return "Нет данных."
    return "\n".join(
        f"- <code>{escape(str(calendar_id))}</code>: {count}"
        for calendar_id, count in events_by_calendar.items()
    )


def _format_calendar_errors(calendar_errors: Dict[str, str]) -> str:
    if not calendar_errors:
        return "Ошибок нет."
    return "\n".join(
        f"- <code>{escape(str(calendar_id))}</code>: {escape(str(error))}"
        for calendar_id, error in calendar_errors.items()
    )


def _checked_calendar_count(context: ContextTypes.DEFAULT_TYPE) -> int:
    settings = _settings(context)
    if settings.use_demo_mode:
        return 1
    return len(settings.google_calendar_ids)


async def _send_events_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    target_date: date,
    date_label: str,
) -> None:
    try:
        events = _service(context).get_events_for_date(target_date)
    except GoogleCalendarNotConfiguredError as error:
        await update.effective_message.reply_text(str(error))
        return
    except GoogleCalendarServiceError as error:
        LOGGER.exception("Google Calendar request failed.")
        await update.effective_message.reply_text(str(error))
        return

    await update.effective_message.reply_text(
        format_events_message(
            events,
            date_label,
            checked_calendar_count=_checked_calendar_count(context),
        ),
        parse_mode=ParseMode.HTML,
    )


def build_application(settings: Settings) -> Application:
    """Create and configure the Telegram application."""
    if not settings.telegram_bot_token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is empty. Copy .env.example to .env "
            "and add a Telegram bot token."
        )
    application = ApplicationBuilder().token(settings.telegram_bot_token).build()
    application.bot_data["settings"] = settings
    demo_service = DemoCalendarService(
        timezone=settings.timezone
    )
    application.bot_data["demo_calendar_service"] = demo_service

    if settings.use_demo_mode:
        application.bot_data["calendar_service"] = demo_service
    else:
        application.bot_data["calendar_service"] = GoogleCalendarService(
            calendar_ids=settings.google_calendar_ids,
            timezone=settings.timezone,
        )

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("health", health_command))
    application.add_handler(CommandHandler("demo", demo_command))
    application.add_handler(CommandHandler("caldebug", caldebug_command))
    application.add_handler(CommandHandler("calendars", calendars_command))
    application.add_handler(CommandHandler("today", today_command))
    application.add_handler(CommandHandler("tomorrow", tomorrow_command))
    return application


def main() -> None:
    settings = get_settings()
    application = build_application(settings)
    mode = "demo" if settings.use_demo_mode else "Google Calendar"
    LOGGER.info("Starting Zerocoder19 Daily Meeting Bot in %s mode.", mode)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
