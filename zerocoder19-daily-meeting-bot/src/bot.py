"""Telegram entry point for Zerocoder19 Daily Meeting Bot."""

from datetime import date, datetime, timedelta
import logging
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
        format_events_message(events, date_label),
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
            calendar_id=settings.google_calendar_id,
            timezone=settings.timezone,
        )

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("health", health_command))
    application.add_handler(CommandHandler("demo", demo_command))
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
