from __future__ import annotations

import asyncio
import logging
from urllib.parse import urljoin

from bs4 import BeautifulSoup
import httpx
from telegram import Bot
from telegram.error import TelegramError

from textile_ai_bot.ai import BriefGenerator
from textile_ai_bot.formatting import telegram_post
from textile_ai_bot.models import Article
from textile_ai_bot.ranker import is_ai_related
from textile_ai_bot.storage import NewsStore

LOGGER = logging.getLogger(__name__)
MAX_PHOTO_CAPTION_LENGTH = 1024


class TelegramPublisher:
    def __init__(self, token: str, chat_id: str) -> None:
        self.chat_id = chat_id
        self.bot = Bot(token=token)

    async def publish(self, article: Article, brief_generator: BriefGenerator) -> None:
        brief = await asyncio.to_thread(brief_generator.generate, article)
        text = telegram_post(article, brief)
        image_url = article.image_url if article.image_url.startswith(("http://", "https://")) else ""
        image_url = image_url or await _fetch_article_image(article.url)
        if image_url:
            try:
                await self.bot.send_photo(
                    chat_id=self.chat_id,
                    photo=image_url,
                    caption=_caption(text),
                    parse_mode="HTML",
                )
                return
            except TelegramError as exc:
                LOGGER.warning("Failed to send article photo, falling back to text: %s", exc)

        await self.bot.send_message(
            chat_id=self.chat_id,
            text=text,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )


async def publish_pending(
    store: NewsStore,
    publisher: TelegramPublisher,
    brief_generator: BriefGenerator,
    *,
    limit: int,
    min_score: int,
) -> int:
    articles = await store.unposted(limit=max(limit * 20, 50), min_score=min_score)
    sent = 0
    skipped = 0
    for article in articles:
        if not is_ai_related(article):
            LOGGER.info("Skipping non-AI article already in queue: %s", article.title)
            await store.mark_posted(article)
            skipped += 1
            continue
        await publisher.publish(article, brief_generator)
        await store.mark_posted(article)
        sent += 1
        LOGGER.info("Published article: %s", article.title)
        if sent >= limit:
            break
    if sent == 0:
        LOGGER.info(
            "No publishable articles sent. Checked %s queued articles, skipped %s non-AI articles.",
            len(articles),
            skipped,
        )
    return sent


def _caption(text: str) -> str:
    if len(text) <= MAX_PHOTO_CAPTION_LENGTH:
        return text
    source_marker = "\n🔗 <b>Источник / Manba:</b>"
    source = ""
    body = text
    if source_marker in text:
        body, source = text.rsplit(source_marker, maxsplit=1)
        source = source_marker + source
    available = MAX_PHOTO_CAPTION_LENGTH - len(source) - 4
    return body[:available].rsplit("\n", 1)[0].rstrip() + "\n..." + source


async def _fetch_article_image(url: str) -> str:
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=10,
            headers={"User-Agent": "MilanaPremiumAITextileBot/0.1"},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
    except httpx.HTTPError:
        return ""

    soup = BeautifulSoup(response.text, "html.parser")
    for selector in (
        'meta[property="og:image"]',
        'meta[name="twitter:image"]',
        'meta[property="twitter:image"]',
    ):
        meta = soup.select_one(selector)
        content = meta.get("content") if meta else ""
        if content:
            return urljoin(url, str(content))

    image = soup.find("img")
    src = image.get("src") if image else ""
    return urljoin(url, str(src)) if src else ""
