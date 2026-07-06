from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True, slots=True)
class Settings:
    telegram_bot_token: str
    telegram_chat_id: str
    openai_api_key: str
    openai_model: str
    database_path: Path
    timezone: str
    morning_brief_time: str
    afternoon_update_time: str
    post_interval_minutes: int
    max_daily_posts: int
    min_importance_score: int
    collection_lookback_hours: int
    health_host: str
    health_port: int
    admin_user_ids: frozenset[int]

    @property
    def openai_enabled(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)


def load_settings() -> Settings:
    load_dotenv()

    admin_ids: set[int] = set()
    for item in _csv(os.getenv("ADMIN_USER_IDS", "")):
        try:
            admin_ids.add(int(item))
        except ValueError:
            continue

    return Settings(
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        database_path=Path(os.getenv("DATABASE_PATH", "./data/news_bot.sqlite3")),
        timezone=os.getenv("TIMEZONE", "Asia/Tashkent"),
        morning_brief_time=os.getenv("MORNING_BRIEF_TIME", "09:00"),
        afternoon_update_time=os.getenv("AFTERNOON_UPDATE_TIME", "15:30"),
        post_interval_minutes=int(os.getenv("POST_INTERVAL_MINUTES", "0")),
        max_daily_posts=int(os.getenv("MAX_DAILY_POSTS", "5")),
        min_importance_score=int(os.getenv("MIN_IMPORTANCE_SCORE", "55")),
        collection_lookback_hours=int(os.getenv("COLLECTION_LOOKBACK_HOURS", "48")),
        health_host=os.getenv("HEALTH_HOST", "0.0.0.0"),
        health_port=int(os.getenv("HEALTH_PORT", "8006")),
        admin_user_ids=frozenset(admin_ids),
    )
