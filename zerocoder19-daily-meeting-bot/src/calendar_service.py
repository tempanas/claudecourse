"""Google Calendar service with local OAuth credentials."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol
from zoneinfo import ZoneInfo

from .zoom_parser import extract_zoom_links


SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CREDENTIALS_FILE = PROJECT_ROOT / "credentials.json"
DEFAULT_TOKEN_FILE = PROJECT_ROOT / "token.json"
GOOGLE_CALENDAR_NOT_CONFIGURED_MESSAGE = (
    "Google Calendar пока не подключён. Включите USE_DEMO_MODE=true "
    "или настройте credentials.json."
)
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
        calendar_id: str,
        timezone: str,
        credentials_file: Path = DEFAULT_CREDENTIALS_FILE,
        token_file: Path = DEFAULT_TOKEN_FILE,
    ) -> None:
        self.calendar_id = calendar_id
        self.timezone = timezone
        self.timezone_info = ZoneInfo(timezone)
        self.credentials_file = Path(credentials_file)
        self.token_file = Path(token_file)
        print("Google Calendar mode enabled", flush=True)

    def get_events_for_date(self, target_date: date) -> List[Dict[str, Any]]:
        """Return normalized events that intersect the requested local day."""
        service = self._build_service()
        day_start = datetime.combine(
            target_date,
            time.min,
            tzinfo=self.timezone_info,
        )
        day_end = day_start + timedelta(days=1)

        events: List[Dict[str, Any]] = []
        page_token: Optional[str] = None

        try:
            while True:
                response = (
                    service.events()
                    .list(
                        calendarId=self.calendar_id,
                        timeMin=day_start.isoformat(),
                        timeMax=day_end.isoformat(),
                        singleEvents=True,
                        orderBy="startTime",
                        timeZone=self.timezone,
                        pageToken=page_token,
                    )
                    .execute()
                )
                events.extend(
                    self._normalize_event(event)
                    for event in response.get("items", [])
                )
                page_token = response.get("nextPageToken")
                if not page_token:
                    break
        except GoogleCalendarNotConfiguredError:
            raise
        except Exception as error:
            raise GoogleCalendarServiceError(
                "Не удалось получить события из Google Calendar. "
                "Проверьте доступ к календарю и настройки API."
            ) from error

        return events

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

    def _normalize_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
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
