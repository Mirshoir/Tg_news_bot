from __future__ import annotations

import logging

from textile_ai_bot.collector import collect_articles
from textile_ai_bot.config import Settings
from textile_ai_bot.dedupe import deduplicate_articles
from textile_ai_bot.ranker import rank_articles
from textile_ai_bot.sources import DEFAULT_SOURCES
from textile_ai_bot.storage import NewsStore

LOGGER = logging.getLogger(__name__)


async def collect_and_store(settings: Settings, store: NewsStore) -> tuple[int, int]:
    articles = await collect_articles(DEFAULT_SOURCES, settings.collection_lookback_hours)
    unique = deduplicate_articles(articles)
    ranked = rank_articles(unique)
    inserted = await store.upsert_ranked(ranked)
    LOGGER.info("Collected %s articles, %s unique, %s new", len(articles), len(unique), inserted)
    return len(unique), inserted
