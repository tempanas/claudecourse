"""Google Calendar service with local OAuth credentials."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Tuple
from zoneinfo import ZoneInfo

from .zoom_parser import extract_zoom_links


SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
MAX_RESULTS = 50
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CREDENTIALS_FILE = PROJECT_ROOT / "credentials.json"
DEFAULT_TOKEN_FILE = PROJECT_ROOT / "token.json"
GOOGLE_CALENDAR_NOT_CONFIGURED_MESSAGE = (
    "Google Calendar пока не подключён. Включите USE_DEMO_MODE=true "
    "или настройте credentials.json."
)
LOGGER = logging.getLogger(__name__)
CREDENTIALS_NOT_FOUND_MESSAGE = (
    "credentials.json не найден в корне проекта. Скачайте OAuth Client ID "
    "типа Desktop app из Google Cloud Console и положите файл в корень проекта."
)


class GoogleCalendarNotConfiguredError(RuntimeError):
    """Raised when OAuth dependencies or local credentials are unavailable."""


class GoogleCalendarServiceError(RuntimeError):
    """Raised when Google Calendar cannot return events."""


class CalendarService(Protocol):
    """Common interface implemented by demo and Google Calendar services."""

    def get_events_for_date(self, target_date: date) -> List[Dict[str, Any]]:
        """Return normalized calendar events for a local date."""


class GoogleCalendarService:
    """Read and normalize events from Google Calendar API."""

    def __init__(
        self,
        calendar_ids: List[str],
        timezone: str,
        credentials_file: Path = DEFAULT_CREDENTIALS_FILE,
        token_file: Path = DEFAULT_TOKEN_FILE,
    ) -> None:
        self.calendar_ids = [
            calendar_id.strip()
            for calendar_id in calendar_ids
            if calendar_id.strip()
        ] or ["primary"]
        self.calendar_id = self.calendar_ids[0]
        self.timezone = timezone
        self.timezone_info = ZoneInfo(timezone)
        self.credentials_file = Path(credentials_file)
        self.token_file = Path(token_file)
        print("Google Calendar mode enabled", flush=True)

    def get_events_for_date(self, target_date: date) -> List[Dict[str, Any]]:
        """Return normalized events that intersect the requested local day."""
        service = self._build_service()
        calendar_names = self._get_calendar_name_map(service)
        fetch_result = self._fetch_events_for_date(service, target_date)

        events = [
            self._normalize_event(
                event,
                calendar_id=calendar_id,
                calendar_name=calendar_names.get(calendar_id, calendar_id),
            )
            for calendar_id, raw_events in fetch_result["events_by_calendar"].items()
            for event in raw_events
        ]
        return sorted(events, key=lambda event: event.get("start", ""))

    def get_day_bounds(self, target_date: date) -> Tuple[datetime, datetime]:
        """Return local start/end datetimes for one calendar day."""
        day_start = datetime.combine(
            target_date,
            time.min,
            tzinfo=self.timezone_info,
        )
        day_end = day_start + timedelta(days=1)
        return day_start, day_end

    def get_debug_info_for_date(self, target_date: date) -> Dict[str, Any]:
        """Return Google Calendar query diagnostics for one local day."""
        service = self._build_service()
        day_start, day_end = self.get_day_bounds(target_date)
        fetch_result = self._fetch_events_for_date(service, target_date)
        events_by_calendar = fetch_result["events_by_calendar"]
        calendar_errors = fetch_result["calendar_errors"]
        event_count = sum(len(events) for events in events_by_calendar.values())

        return {
            "calendar_ids": self.calendar_ids,
            "time_min": day_start.isoformat(),
            "time_max": day_end.isoformat(),
            "checked_calendar_count": len(self.calendar_ids),
            "events_by_calendar": {
                calendar_id: len(events)
                for calendar_id, events in events_by_calendar.items()
            },
            "calendar_errors": calendar_errors,
            "event_count": event_count,
            "event_titles": [
                event.get("summary") or "Без названия"
                for events in events_by_calendar.values()
                for event in events
            ],
        }

    def list_calendars(self) -> List[Dict[str, Any]]:
        """Return calendars available to the authorized Google account."""
        service = self._build_service()
        return self._list_calendars_with_service(service)

    def _list_calendars_with_service(self, service: Any) -> List[Dict[str, Any]]:
        """Return calendars using an already built Google Calendar service."""
        calendars: List[Dict[str, Any]] = []
        page_token: Optional[str] = None

        try:
            while True:
                response = (
                    service.calendarList()
                    .list(pageToken=page_token)
                    .execute()
                )
                calendars.extend(response.get("items", []))
                page_token = response.get("nextPageToken")
                if not page_token:
                    break
        except GoogleCalendarNotConfiguredError:
            raise
        except Exception as error:
            raise GoogleCalendarServiceError(
                "Не удалось получить список календарей Google Calendar. "
                "Проверьте доступ к аккаунту и настройки API."
            ) from error

        LOGGER.info("Google Calendar API returned %s calendars", len(calendars))
        for calendar in calendars:
            LOGGER.info(
                "Google Calendar list item: summary=%s id=%s primary=%s accessRole=%s",
                calendar.get("summary", ""),
                calendar.get("id", ""),
                calendar.get("primary", False),
                calendar.get("accessRole", ""),
            )

        return calendars

    def _fetch_events_for_date(
        self,
        service: Any,
        target_date: date,
    ) -> Dict[str, Any]:
        day_start, day_end = self.get_day_bounds(target_date)
        events_by_calendar: Dict[str, List[Dict[str, Any]]] = {}
        calendar_errors: Dict[str, str] = {}

        LOGGER.info("Google Calendar calendar_ids=%s", self.calendar_ids)
        LOGGER.info("Google Calendar timeMin=%s", day_start.isoformat())
        LOGGER.info("Google Calendar timeMax=%s", day_end.isoformat())

        for calendar_id in self.calendar_ids:
            raw_events: List[Dict[str, Any]] = []
            page_token: Optional[str] = None
            LOGGER.info("Reading Google Calendar calendar_id=%s", calendar_id)

            try:
                while True:
                    response = (
                        service.events()
                        .list(
                            calendarId=calendar_id,
                            timeMin=day_start.isoformat(),
                            timeMax=day_end.isoformat(),
                            singleEvents=True,
                            orderBy="startTime",
                            maxResults=MAX_RESULTS,
                            timeZone=self.timezone,
                            pageToken=page_token,
                        )
                        .execute()
                    )
                    page_events = response.get("items", [])
                    raw_events.extend(page_events)
                    LOGGER.info(
                        "Google Calendar API page returned %s events for calendar_id=%s",
                        len(page_events),
                        calendar_id,
                    )
                    page_token = response.get("nextPageToken")
                    if not page_token:
                        break
            except GoogleCalendarNotConfiguredError:
                raise
            except Exception as error:
                calendar_errors[calendar_id] = str(error)
                LOGGER.exception(
                    "Failed to read Google Calendar calendar_id=%s",
                    calendar_id,
                )

            events_by_calendar[calendar_id] = raw_events
            LOGGER.info(
                "Google Calendar API returned %s events for calendar_id=%s",
                len(raw_events),
                calendar_id,
            )
            if len(raw_events) == 1:
                LOGGER.info(
                    "Only 1 event found for calendar_id=%s timeMin=%s timeMax=%s",
                    calendar_id,
                    day_start.isoformat(),
                    day_end.isoformat(),
                )

            for event in raw_events:
                LOGGER.info(
                    "Google Calendar event title from calendar_id=%s: %s",
                    calendar_id,
                    event.get("summary") or "Без названия",
                )

        LOGGER.info(
            "Google Calendar API returned %s events total",
            sum(len(events) for events in events_by_calendar.values()),
        )

        return {
            "events_by_calendar": events_by_calendar,
            "calendar_errors": calendar_errors,
        }

    def _get_calendar_name_map(self, service: Any) -> Dict[str, str]:
        try:
            calendars = self._list_calendars_with_service(service)
        except Exception:
            LOGGER.exception("Failed to load Google Calendar names.")
            return {}

        return {
            str(calendar.get("id")): str(calendar.get("summary") or calendar.get("id"))
            for calendar in calendars
            if calendar.get("id")
        }

    def _build_service(self) -> Any:
        if not self.credentials_file.exists():
            raise GoogleCalendarNotConfiguredError(CREDENTIALS_NOT_FOUND_MESSAGE)

        print("credentials.json found", flush=True)

        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except ImportError as error:
            raise GoogleCalendarNotConfiguredError(
                GOOGLE_CALENDAR_NOT_CONFIGURED_MESSAGE
            ) from error

        credentials = None

        if self.token_file.exists():
            try:
                credentials = Credentials.from_authorized_user_file(
                    str(self.token_file),
                    SCOPES,
                )
            except (OSError, ValueError) as error:
                raise GoogleCalendarNotConfiguredError(
                    GOOGLE_CALENDAR_NOT_CONFIGURED_MESSAGE
                ) from error

        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                try:
                    credentials.refresh(Request())
                except Exception as error:
                    raise GoogleCalendarNotConfiguredError(
                        GOOGLE_CALENDAR_NOT_CONFIGURED_MESSAGE
                    ) from error
            else:
                if not self.credentials_file.exists():
                    raise GoogleCalendarNotConfiguredError(CREDENTIALS_NOT_FOUND_MESSAGE)

                try:
                    print("Starting Google OAuth flow", flush=True)
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self.credentials_file),
                        SCOPES,
                    )
                    credentials = flow.run_local_server(port=0)
                except Exception as error:
                    raise GoogleCalendarNotConfiguredError(
                        GOOGLE_CALENDAR_NOT_CONFIGURED_MESSAGE
                    ) from error

            try:
                self.token_file.write_text(
                    credentials.to_json(),
                    encoding="utf-8",
                )
                print("token.json saved", flush=True)
            except OSError as error:
                raise GoogleCalendarNotConfiguredError(
                    GOOGLE_CALENDAR_NOT_CONFIGURED_MESSAGE
                ) from error

        return build(
            "calendar",
            "v3",
            credentials=credentials,
            cache_discovery=False,
        )

    def _normalize_event(
        self,
        event: Dict[str, Any],
        calendar_id: str,
        calendar_name: str,
    ) -> Dict[str, Any]:
        description = str(event.get("description") or "")
        location = str(event.get("location") or "")
        hangout_link = str(event.get("hangoutLink") or "")
        conference_uris = self._conference_entry_point_uris(event)

        zoom_sources = [description, location, hangout_link]
        zoom_sources.extend(conference_uris)
        zoom_links = extract_zoom_links("\n".join(zoom_sources))

        if zoom_links:
            description_parts = [description] if description else []
            description_parts.append("\n".join(zoom_links))
            description = "\n".join(description_parts)

        return {
            "id": event.get("id", ""),
            "title": event.get("summary") or "Без названия",
            "start": self._normalize_event_time(event.get("start", {})),
            "end": self._normalize_event_time(event.get("end", {})),
            "description": description,
            "location": location,
            "attendees": [],
            "source_calendar_id": calendar_id,
            "source_calendar_name": calendar_name or calendar_id,
        }

    def _conference_entry_point_uris(
        self,
        event: Dict[str, Any],
    ) -> List[str]:
        conference_data = event.get("conferenceData") or {}
        entry_points = conference_data.get("entryPoints") or []
        return [
            str(entry_point.get("uri", ""))
            for entry_point in entry_points
            if entry_point.get("uri")
        ]

    def _normalize_event_time(self, event_time: Dict[str, Any]) -> str:
        date_time_value = event_time.get("dateTime")
        if date_time_value:
            return str(date_time_value)

        date_value = event_time.get("date")
        if date_value:
            local_midnight = datetime.combine(
                date.fromisoformat(str(date_value)),
                time.min,
                tzinfo=self.timezone_info,
            )
            return local_midnight.isoformat()

        return ""
