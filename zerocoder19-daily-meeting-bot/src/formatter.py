"""Telegram message formatting for calendar events."""

from datetime import datetime
from html import escape
from typing import Any, Dict, List, Optional

from .zoom_parser import extract_zoom_links


def _event_text(event: Dict[str, Any]) -> str:
    return " ".join(
        str(event.get(field, ""))
        for field in ("title", "description", "location")
    )


def _format_time(value: str) -> str:
    try:
        return datetime.fromisoformat(value).strftime("%H:%M")
    except (TypeError, ValueError):
        return "время не указано"


def get_calendar_display_name(calendar_id: str) -> str:
    """Return a user-facing calendar name without changing internal IDs."""
    if calendar_id == "primary":
        return "ZerocoderTeen"
    return calendar_id


def format_events_message(
    events: List[Dict[str, Any]],
    date_label: str,
    checked_calendar_count: Optional[int] = None,
) -> str:
    """Build an HTML-formatted Telegram message for a list of events."""
    if checked_calendar_count is None:
        checked_calendar_count = len(
            {
                str(event.get("source_calendar_id") or "demo")
                for event in events
            }
        ) or 1

    if not events:
        return (
            f"📅 <b>{escape(date_label)}</b>\n\n"
            "Найдено встреч: 0\n"
            f"Проверено календарей: {checked_calendar_count}\n\n"
            "Встреч не найдено. Расписание свободно."
        )

    lines = [
        f"📅 <b>{escape(date_label)}</b>",
        f"Найдено встреч: {len(events)}",
        f"Проверено календарей: {checked_calendar_count}",
    ]

    for index, event in enumerate(events, start=1):
        zoom_links = extract_zoom_links(_event_text(event))
        start_time = _format_time(event.get("start", ""))
        end_time = _format_time(event.get("end", ""))

        lines.extend(
            [
                "",
                f"<b>{index}. {escape(str(event.get('title', 'Без названия')))}</b>",
                f"🕒 {start_time} - {end_time}",
            ]
        )

        source_calendar = (
            event.get("source_calendar_name")
            or event.get("source_calendar_id")
            or "не указан"
        )
        source_calendar = get_calendar_display_name(str(source_calendar))
        lines.append(f"Календарь: {escape(str(source_calendar))}")

        attendees = event.get("attendees") or []
        if attendees:
            lines.append(f"Участники: {escape(', '.join(attendees))}")

        if zoom_links:
            lines.append("Zoom: найден ✅")
            lines.append(f"Ссылка: {escape(zoom_links[0])}")
        else:
            lines.append("Zoom: не найден ⚠️")
            lines.append("Действие: проверить событие в календаре.")

    return "\n".join(lines)
