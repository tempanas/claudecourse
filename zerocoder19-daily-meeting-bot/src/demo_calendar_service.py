"""Demo calendar service backed by anonymized JSON fixtures."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
import json
from pathlib import Path
from typing import Any, Dict, List, Union
from zoneinfo import ZoneInfo


DEFAULT_DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "sample_events.json"


class DemoCalendarService:
    """Read reusable demo events and place them on dates relative to today."""

    def __init__(
        self,
        data_file: Union[Path, str] = DEFAULT_DATA_FILE,
        timezone: str = "Europe/Minsk",
    ) -> None:
        self.data_file = Path(data_file)
        self.timezone = ZoneInfo(timezone)

    def get_events_for_date(self, target_date: date) -> List[Dict[str, Any]]:
        """Return demo events scheduled for the requested local date."""
        local_today = datetime.now(self.timezone).date()
        day_offset = (target_date - local_today).days
        events = self._load_events()

        result = [
            self._materialize_event(event, target_date)
            for event in events
            if event.get("day_offset") == day_offset
        ]
        return sorted(result, key=lambda event: event["start"])

    def get_today_events(self) -> List[Dict[str, Any]]:
        local_today = datetime.now(self.timezone).date()
        return self.get_events_for_date(local_today)

    def get_tomorrow_events(self) -> List[Dict[str, Any]]:
        local_today = datetime.now(self.timezone).date()
        return self.get_events_for_date(local_today + timedelta(days=1))

    def _load_events(self) -> List[Dict[str, Any]]:
        with self.data_file.open(encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, list):
            raise ValueError("Demo events file must contain a JSON array.")
        return data

    def _materialize_event(
        self,
        event: Dict[str, Any],
        target_date: date,
    ) -> Dict[str, Any]:
        start = datetime.combine(
            target_date,
            time.fromisoformat(event["start_time"]),
            tzinfo=self.timezone,
        )
        end = datetime.combine(
            target_date,
            time.fromisoformat(event["end_time"]),
            tzinfo=self.timezone,
        )

        return {
            "id": event["id"],
            "title": event["title"],
            "start": start.isoformat(),
            "end": end.isoformat(),
            "description": event.get("description", ""),
            "location": event.get("location", ""),
            "attendees": event.get("attendees", []),
            "source_calendar_id": "demo",
            "source_calendar_name": "Demo calendar",
        }
