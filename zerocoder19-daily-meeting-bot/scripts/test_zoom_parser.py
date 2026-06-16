"""Small unit-like checks for Zoom URL extraction and normalization."""

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.zoom_parser import extract_zoom_links, normalize_zoom_url  # noqa: E402


def test_regular_zoom_url_is_preserved() -> None:
    url = "https://us02web.zoom.us/j/81989422129?pwd=demo_only"
    assert normalize_zoom_url(url) == url
    assert extract_zoom_links(f"Join: {url}") == [url]


def test_html_entities_are_cleaned() -> None:
    text = (
        "https://us02web.zoom.us/j/81989422129"
        "?pwd=demo_only&amp;sa=D&amp;source=calendar"
    )
    assert extract_zoom_links(text) == [
        "https://us02web.zoom.us/j/81989422129?pwd=demo_only"
    ]


def test_percent_encoded_pwd_is_decoded() -> None:
    text = "https://us02web.zoom.us/j/81989422129?pwd%3Ddemo_only"
    assert extract_zoom_links(text) == [
        "https://us02web.zoom.us/j/81989422129?pwd=demo_only"
    ]


def test_google_calendar_params_are_removed() -> None:
    text = (
        "https://us02web.zoom.us/j/81989422129"
        "?pwd%3Ddemo_only&amp;sa=D&amp;source=calendar&amp;usd=2&amp;usg=abc"
    )
    assert extract_zoom_links(text) == [
        "https://us02web.zoom.us/j/81989422129?pwd=demo_only"
    ]


if __name__ == "__main__":
    test_regular_zoom_url_is_preserved()
    test_html_entities_are_cleaned()
    test_percent_encoded_pwd_is_decoded()
    test_google_calendar_params_are_removed()
    print("zoom_parser tests OK")
