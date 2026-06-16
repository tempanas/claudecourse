"""Utilities for finding Zoom meeting links in calendar text."""

from html import unescape
import re
from typing import List, Set
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit, urlunsplit


ZOOM_URL_PATTERN = re.compile(
    r"https?://(?:[a-z0-9-]+\.)*zoom\.us(?:/[^\s<>'\"\]\[{}()]*)?",
    flags=re.IGNORECASE,
)
ALLOWED_ZOOM_QUERY_PARAMS = {"pwd", "tk", "zak", "uname", "stype", "action"}
GOOGLE_CALENDAR_QUERY_PARAMS = {"sa", "source", "usd", "usg"}


def _is_zoom_host(hostname: str) -> bool:
    hostname = hostname.lower().rstrip(".")
    return hostname == "zoom.us" or hostname.endswith(".zoom.us")


def normalize_zoom_url(url: str) -> str:
    """Return a cleaned Zoom URL or an empty string for non-Zoom URLs."""
    if not url:
        return ""

    cleaned_url = unquote(unescape(url.strip()).rstrip(".,;:!?"))
    parsed = urlsplit(cleaned_url)

    if parsed.scheme not in {"http", "https"}:
        return ""
    if not parsed.hostname or not _is_zoom_host(parsed.hostname):
        return ""

    query_items = parse_qsl(parsed.query, keep_blank_values=True)
    filtered_query_items = [
        (key, value)
        for key, value in query_items
        if key in ALLOWED_ZOOM_QUERY_PARAMS
        and key not in GOOGLE_CALENDAR_QUERY_PARAMS
    ]

    path = quote(unquote(parsed.path), safe="/")
    query = urlencode(filtered_query_items, doseq=True)

    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc.lower(),
            path,
            query,
            "",
        )
    )


def extract_zoom_links(text: str) -> List[str]:
    """Return unique Zoom URLs found in text, preserving their order."""
    if not text:
        return []

    normalized_text = unquote(unescape(text))
    links: List[str] = []
    seen: Set[str] = set()

    for match in ZOOM_URL_PATTERN.finditer(normalized_text):
        link = normalize_zoom_url(match.group(0))
        if not link:
            continue
        if link not in seen:
            seen.add(link)
            links.append(link)

    return links
