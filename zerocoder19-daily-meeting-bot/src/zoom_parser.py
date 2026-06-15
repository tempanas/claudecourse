"""Utilities for finding Zoom meeting links in calendar text."""

import re
from typing import List, Set


ZOOM_URL_PATTERN = re.compile(
    r"https?://(?:[a-z0-9-]+\.)*zoom\.us(?:/[^\s<>'\"\]\[{}()]*)?",
    flags=re.IGNORECASE,
)


def extract_zoom_links(text: str) -> List[str]:
    """Return unique Zoom URLs found in text, preserving their order."""
    if not text:
        return []

    links: List[str] = []
    seen: Set[str] = set()

    for match in ZOOM_URL_PATTERN.finditer(text):
        link = match.group(0).rstrip(".,;:!?")
        if link not in seen:
            seen.add(link)
            links.append(link)

    return links
