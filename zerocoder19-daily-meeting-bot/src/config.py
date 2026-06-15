"""Application configuration loaded from environment variables."""

from dataclasses import dataclass
import os
from typing import Optional

from dotenv import load_dotenv


load_dotenv()


def _as_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    google_calendar_id: str
    timezone: str
    use_demo_mode: bool


def get_settings() -> Settings:
    """Return settings from the current environment."""
    return Settings(
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        google_calendar_id=os.getenv("GOOGLE_CALENDAR_ID", "primary"),
        timezone=os.getenv("TIMEZONE", "Europe/Minsk"),
        use_demo_mode=_as_bool(os.getenv("USE_DEMO_MODE"), default=True),
    )
