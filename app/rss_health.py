from __future__ import annotations

from dataclasses import dataclass
from urllib.error import URLError
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET


@dataclass
class FeedHealthResult:
    healthy: bool
    message: str


def check_feed_health(url: str, timeout_seconds: int = 8) -> FeedHealthResult:
    request = Request(url, headers={"User-Agent": "podcast-generator/0.1"})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = response.read(1024 * 1024)
    except URLError as error:
        return FeedHealthResult(False, f"Network error: {error.reason}")
    except Exception as error:  # pragma: no cover - defensive path
        return FeedHealthResult(False, f"Request failed: {error}")

    try:
        root = ET.fromstring(payload)
    except ET.ParseError as error:
        return FeedHealthResult(False, f"Invalid XML: {error}")

    tag = root.tag.lower()
    if tag.endswith("rss") or tag.endswith("feed"):
        return FeedHealthResult(True, "Feed is reachable and parseable")

    return FeedHealthResult(False, f"Unsupported feed root tag: {root.tag}")
