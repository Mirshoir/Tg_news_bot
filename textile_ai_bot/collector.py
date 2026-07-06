from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Iterable
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup
import feedparser
import httpx

from textile_ai_bot.models import Article, NewsSource
from textile_ai_bot.text_utils import clean_text

LOGGER = logging.getLogger(__name__)


def _entry_datetime(entry: dict) -> datetime:
    for key in ("published", "updated", "created"):
        value = entry.get(key)
        if not value:
            continue
        try:
            parsed = parsedate_to_datetime(value)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except (TypeError, ValueError):
            continue
    return datetime.now(timezone.utc)


def _entry_summary(entry: dict) -> str:
    for key in ("summary", "description"):
        value = entry.get(key)
        if value:
            return clean_text(str(value), limit=900)
    return ""


def _entry_image_url(entry: dict) -> str:
    media_content = entry.get("media_content") or []
    for item in media_content:
        url = item.get("url") if isinstance(item, dict) else ""
        if url:
            return str(url)

    media_thumbnail = entry.get("media_thumbnail") or []
    for item in media_thumbnail:
        url = item.get("url") if isinstance(item, dict) else ""
        if url:
            return str(url)

    for enclosure in entry.get("enclosures") or []:
        href = enclosure.get("href") if isinstance(enclosure, dict) else ""
        mime_type = enclosure.get("type", "") if isinstance(enclosure, dict) else ""
        if href and str(mime_type).startswith("image/"):
            return str(href)

    for link in entry.get("links") or []:
        href = link.get("href") if isinstance(link, dict) else ""
        mime_type = link.get("type", "") if isinstance(link, dict) else ""
        if href and str(mime_type).startswith("image/"):
            return str(href)

    content = " ".join(
        str(item.get("value", ""))
        for item in entry.get("content") or []
        if isinstance(item, dict)
    )
    soup = BeautifulSoup(f"{entry.get('summary', '')} {content}", "html.parser")
    image = soup.find("img")
    src = image.get("src") if image else ""
    return str(src or "")


async def _fetch_source(client: httpx.AsyncClient, source: NewsSource) -> list[Article]:
    try:
        response = await client.get(source.url)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        LOGGER.warning("Failed to fetch %s: %s", source.name, exc)
        return []

    if source.kind == "html":
        return _parse_html_source(source, response.text)

    feed = feedparser.parse(response.content)
    articles: list[Article] = []
    for entry in feed.entries:
        title = str(entry.get("title", "")).strip()
        link = str(entry.get("link", "")).strip()
        if not title or not link:
            continue

        articles.append(
            Article(
                source_name=source.name,
                source_url=source.url,
                title=title,
                url=link,
                category=source.category,
                summary=_entry_summary(entry),
                image_url=_entry_image_url(entry),
                published_at=_entry_datetime(entry),
                raw=dict(entry),
            )
        )
    return articles


def _parse_html_source(source: NewsSource, html: str) -> list[Article]:
    soup = BeautifulSoup(html, "html.parser")
    source_host = urlsplit(source.url).netloc.removeprefix("www.")
    articles: list[Article] = []
    seen: set[str] = set()

    for link in soup.select("a[href]"):
        title = " ".join(link.get_text(" ", strip=True).split())
        if len(title) < 18 or len(title) > 180:
            continue

        href = urljoin(source.url, link.get("href", ""))
        parsed = urlsplit(href)
        host = parsed.netloc.removeprefix("www.")
        if source_host and host and host != source_host:
            continue
        if source.link_patterns and not any(pattern in parsed.path for pattern in source.link_patterns):
            continue
        if href in seen:
            continue

        parent_text = ""
        parent = link.find_parent(["article", "li", "div"])
        if parent:
            parent_text = " ".join(parent.get_text(" ", strip=True).split())
            image = parent.find("img")
            image_url = urljoin(source.url, image.get("src", "")) if image else ""
        else:
            image_url = ""
        if parent_text == title:
            parent_text = ""

        seen.add(href)
        articles.append(
            Article(
                source_name=source.name,
                source_url=source.url,
                title=title,
                url=href,
                category=source.category,
                summary=clean_text(parent_text, limit=800),
                image_url=image_url,
                published_at=datetime.now(timezone.utc),
                raw={},
            )
        )
        if len(articles) >= 25:
            break

    return articles


async def collect_articles(
    sources: Iterable[NewsSource],
    lookback_hours: int,
    timeout_seconds: float = 15.0,
) -> list[Article]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    headers = {"User-Agent": "MilanaPremiumAITextileBot/0.1"}
    async with httpx.AsyncClient(
        follow_redirects=True,
        headers=headers,
        timeout=timeout_seconds,
    ) as client:
        batches = await asyncio.gather(*[_fetch_source(client, source) for source in sources])

    articles = [article for batch in batches for article in batch]
    return [article for article in articles if article.published_at >= cutoff]
