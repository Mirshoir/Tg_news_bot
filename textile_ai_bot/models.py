from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class NewsSource:
    name: str
    url: str
    category: str
    priority: int = 50
    language: str = "en"
    kind: str = "rss"
    link_patterns: tuple[str, ...] = ()


@dataclass(slots=True)
class Article:
    source_name: str
    source_url: str
    title: str
    url: str
    category: str
    summary: str = ""
    image_url: str = ""
    published_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RankedArticle:
    article: Article
    score: int
    reasons: list[str]


@dataclass(slots=True)
class IntelligenceBrief:
    title_ru: str
    title_uz: str
    summary_ru: str
    summary_uz: str
    highlights_ru: list[str]
    highlights_uz: list[str]
    why_it_matters_ru: str
    why_it_matters_uz: str
    milana_opportunity_ru: str
    milana_opportunity_uz: str
