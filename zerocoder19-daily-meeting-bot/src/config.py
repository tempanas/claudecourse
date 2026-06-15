"""Application configuration loaded from environment variables."""

from dataclasses import dataclass
import os
from typing import List, Optional

from dotenv import load_dotenv


load_dotenv()


def _as_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _clean_values(values: List[Optional[str]]) -> List[str]:
    return [
        value.strip()
        for value in values
        if value and value.strip()
    ]


def _split_calendar_ids(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return _clean_values(value.split(","))


def _get_google_calendar_ids() -> List[str]:
    numbered_calendar_ids = _clean_values(
        [
            os.getenv("GOOGLE_CALENDAR_ID_1"),
            os.getenv("GOOGLE_CALENDAR_ID_2"),
            os.getenv("GOOGLE_CALENDAR_ID_3"),
            os.getenv("GOOGLE_CALENDAR_ID_4"),
            os.getenv("GOOGLE_CALENDAR_ID_5"),
        ]
    )
    if numbered_calendar_ids:
        return numbered_calendar_ids

    calendar_ids = _split_calendar_ids(os.getenv("GOOGLE_CALENDAR_IDS"))
    if calendar_ids:
        return calendar_ids

    legacy_calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "").strip()
    if legacy_calendar_id:
        return [legacy_calendar_id]

    return ["primary"]


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    google_calendar_id: str
    google_calendar_ids: List[str]
    timezone: str
    use_demo_mode: bool


def get_settings() -> Settings:
    """Return settings from the current environment."""
    google_calendar_ids = _get_google_calendar_ids()
    return Settings(
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        google_calendar_id=google_calendar_ids[0],
        google_calendar_ids=google_calendar_ids,
        timezone=os.getenv("TIMEZONE", "Europe/Minsk"),
        use_demo_mode=_as_bool(os.getenv("USE_DEMO_MODE"), default=True),
    )
