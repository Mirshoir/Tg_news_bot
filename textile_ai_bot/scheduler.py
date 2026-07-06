from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from textile_ai_bot.ai import BriefGenerator
from textile_ai_bot.config import Settings
from textile_ai_bot.publisher import TelegramPublisher, publish_pending
from textile_ai_bot.service import collect_and_store
from textile_ai_bot.storage import NewsStore

LOGGER = logging.getLogger(__name__)


def _hour_minute(value: str) -> tuple[int, int]:
    hour, minute = value.split(":", maxsplit=1)
    return int(hour), int(minute)


def build_scheduler(
    settings: Settings,
    store: NewsStore,
    publisher: TelegramPublisher,
    brief_generator: BriefGenerator,
) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=settings.timezone)

    async def briefing_job() -> None:
        if await store.get_state("paused", "0") == "1":
            LOGGER.info("Scheduled posting paused")
            return
        await collect_and_store(settings, store)
        await publish_pending(
            store,
            publisher,
            brief_generator,
            limit=settings.max_daily_posts,
            min_score=settings.min_importance_score,
        )

    if settings.post_interval_minutes > 0:
        scheduler.add_job(
            briefing_job,
            IntervalTrigger(minutes=settings.post_interval_minutes, timezone=settings.timezone),
            id="interval_news_update",
            replace_existing=True,
        )
        LOGGER.info("Scheduled news updates every %s minutes", settings.post_interval_minutes)
        return scheduler

    morning_hour, morning_minute = _hour_minute(settings.morning_brief_time)
    afternoon_hour, afternoon_minute = _hour_minute(settings.afternoon_update_time)
    scheduler.add_job(
        briefing_job,
        CronTrigger(hour=morning_hour, minute=morning_minute, timezone=settings.timezone),
        id="morning_briefing",
        replace_existing=True,
    )
    scheduler.add_job(
        briefing_job,
        CronTrigger(hour=afternoon_hour, minute=afternoon_minute, timezone=settings.timezone),
        id="afternoon_update",
        replace_existing=True,
    )
    return scheduler
