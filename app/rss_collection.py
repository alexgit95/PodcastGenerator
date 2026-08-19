from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
from typing import Any
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET


def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None

    # Try RFC822 first (typical RSS pubDate), then ISO variants.
    for fmt in (
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
    ):
        try:
            parsed = datetime.strptime(text, fmt)
            return _to_utc(parsed)
        except ValueError:
            continue

    try:
        normalized = text.replace("Z", "+00:00")
        return _to_utc(datetime.fromisoformat(normalized))
    except ValueError:
        return None


def _node_text(parent: ET.Element, tags: tuple[str, ...]) -> str | None:
    for tag in tags:
        node = parent.find(tag)
        if node is not None and node.text:
            content = node.text.strip()
            if content:
                return content
    return None


def _canonical_key(link: str | None, title: str | None) -> str:
    raw = (link or "") + "|" + (title or "")
    return hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()


@dataclass
class CollectedItem:
    item_key: str
    title: str
    link: str
    published_at: datetime
    source_id: str
    source_title: str
    category_id: str
    category_name: str


def _extract_items_from_rss(root: ET.Element) -> list[dict[str, Any]]:
    channel = root.find("channel")
    if channel is None:
        return []

    items: list[dict[str, Any]] = []
    for node in channel.findall("item"):
        title = _node_text(node, ("title",))
        link = _node_text(node, ("link",))
        published_text = _node_text(node, ("pubDate", "{http://purl.org/dc/elements/1.1/}date"))
        published_at = _parse_datetime(published_text)
        if not title or not link or not published_at:
            continue
        items.append({"title": title, "link": link, "published_at": published_at})
    return items


def _extract_items_from_atom(root: ET.Element) -> list[dict[str, Any]]:
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    items: list[dict[str, Any]] = []
    for entry in root.findall("atom:entry", ns):
        title = _node_text(entry, ("{http://www.w3.org/2005/Atom}title",))
        link = None
        for link_node in entry.findall("atom:link", ns):
            href = link_node.attrib.get("href", "").strip()
            if href:
                link = href
                break
        published_text = _node_text(
            entry,
            (
                "{http://www.w3.org/2005/Atom}updated",
                "{http://www.w3.org/2005/Atom}published",
            ),
        )
        published_at = _parse_datetime(published_text)
        if not title or not link or not published_at:
            continue
        items.append({"title": title, "link": link, "published_at": published_at})
    return items


def _fetch_source_items(url: str, timeout_seconds: int = 8) -> list[dict[str, Any]]:
    request = Request(url, headers={"User-Agent": "podcast-generator/0.1"})
    with urlopen(request, timeout=timeout_seconds) as response:
        payload = response.read(1024 * 1024)
    root = ET.fromstring(payload)
    tag = root.tag.lower()
    if tag.endswith("rss"):
        return _extract_items_from_rss(root)
    if tag.endswith("feed"):
        return _extract_items_from_atom(root)
    return []


def collect_fresh_items(bindings: list[dict[str, Any]], max_age_hours: int) -> dict[str, list[CollectedItem]]:
    now_utc = datetime.now(timezone.utc)
    freshness_limit = now_utc - timedelta(hours=max_age_hours)

    source_cache: dict[str, list[dict[str, Any]]] = {}
    by_category: dict[str, list[CollectedItem]] = {}

    for binding in bindings:
        category_id = binding["category_id"]
        by_category.setdefault(category_id, [])
        source_id = binding["source_id"]
        source_url = binding["source_url"]

        if source_id not in source_cache:
            try:
                source_cache[source_id] = _fetch_source_items(source_url)
            except Exception:
                source_cache[source_id] = []

        for item in source_cache[source_id]:
            published_at = item["published_at"]
            if published_at < freshness_limit:
                continue
            key = _canonical_key(item["link"], item["title"])
            by_category[category_id].append(
                CollectedItem(
                    item_key=key,
                    title=item["title"],
                    link=item["link"],
                    published_at=published_at,
                    source_id=source_id,
                    source_title=binding["source_title"],
                    category_id=category_id,
                    category_name=binding["category_name"],
                )
            )

        by_category[category_id].sort(key=lambda entry: entry.published_at, reverse=True)

    return by_category
