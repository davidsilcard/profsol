from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET

import requests
from django.conf import settings
from django.utils.dateparse import parse_datetime

from atelier.models import Video


logger = logging.getLogger(__name__)

YOUTUBE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
    )
}
CHANNEL_ID_PATTERN = re.compile(r'"externalId":"(UC[\w-]+)"')
ATOM_NAMESPACE = {"atom": "http://www.w3.org/2005/Atom", "media": "http://search.yahoo.com/mrss/"}


class YouTubeSyncError(Exception):
    pass


def resolve_channel_id(channel_url: str) -> str:
    response = requests.get(channel_url, headers=YOUTUBE_HEADERS, timeout=15)
    response.raise_for_status()
    match = CHANNEL_ID_PATTERN.search(response.text)
    if not match:
        raise YouTubeSyncError("Não foi possível identificar o channel_id do YouTube.")
    return match.group(1)


def fetch_feed_entries(channel_url: str) -> list[dict]:
    channel_id = resolve_channel_id(channel_url)
    feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    response = requests.get(feed_url, headers=YOUTUBE_HEADERS, timeout=15)
    response.raise_for_status()

    root = ET.fromstring(response.text)
    entries: list[dict] = []

    for entry in root.findall("atom:entry", ATOM_NAMESPACE):
        video_id = entry.findtext("yt:videoId", namespaces={"yt": "http://www.youtube.com/xml/schemas/2015"})
        link = entry.find("atom:link", ATOM_NAMESPACE)
        group = entry.find("media:group", ATOM_NAMESPACE)
        thumbnail = group.find("media:thumbnail", ATOM_NAMESPACE) if group is not None else None
        description = group.findtext("media:description", default="", namespaces=ATOM_NAMESPACE) if group else ""

        if not video_id or link is None:
            continue

        entries.append(
            {
                "youtube_id": video_id,
                "youtube_url": link.attrib.get("href", f"https://www.youtube.com/watch?v={video_id}"),
                "title": entry.findtext("atom:title", default="", namespaces=ATOM_NAMESPACE),
                "description": description,
                "thumbnail_url": thumbnail.attrib.get("url", "") if thumbnail is not None else "",
                "published_at": parse_datetime(
                    entry.findtext("atom:published", default="", namespaces=ATOM_NAMESPACE)
                ),
            }
        )

    return entries


def sync_channel_videos(channel_url: str | None = None, limit: int = 18) -> int:
    resolved_url = channel_url or settings.YOUTUBE_CHANNEL_URL
    entries = fetch_feed_entries(resolved_url)[:limit]
    synced = 0

    for item in entries:
        Video.objects.update_or_create(
            youtube_id=item["youtube_id"],
            defaults={
                "title": item["title"],
                "youtube_url": item["youtube_url"],
                "thumbnail_url": item["thumbnail_url"],
                "description": item["description"],
                "published_at": item["published_at"],
                "is_published": True,
            },
        )
        synced += 1

    return synced


def sync_on_demand_if_needed() -> None:
    if not settings.YOUTUBE_SYNC_ON_DEMAND:
        return
    if Video.objects.filter(is_published=True).exists():
        return
    try:
        sync_channel_videos()
    except Exception as exc:  # pragma: no cover - falha externa
        logger.warning("Falha ao sincronizar vídeos do YouTube: %s", exc)
