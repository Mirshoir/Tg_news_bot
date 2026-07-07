from __future__ import annotations

import re
from datetime import datetime, timezone

from textile_ai_bot.models import Article, RankedArticle

HIGH_SIGNAL_TERMS = {
    "ai": 30,
    "artificial intelligence": 35,
    "machine learning": 32,
    "deep learning": 30,
    "generative ai": 30,
    "llm": 24,
    "neural network": 24,
    "fabric defect": 35,
    "defect detection": 35,
    "quality control": 30,
    "computer vision": 30,
    "smart factory": 28,
    "predictive maintenance": 28,
    "textile manufacturing": 28,
    "production optimization": 25,
    "automation": 22,
    "supply chain": 18,
    "sustainability": 16,
    "demand forecasting": 24,
    "inventory optimization": 22,
    "virtual try-on": 20,
    "ai merchandising": 20,
    "open source": 12,
    "model release": 14,
}

CATEGORY_BOOSTS = {
    "textile": 28,
    "fashion": 20,
    "open_source": 16,
    "general_ai": 10,
}

GENERAL_AI_COMPANIES = (
    "openai",
    "anthropic",
    "deepmind",
    "nvidia",
    "meta ai",
    "microsoft",
    "hugging face",
    "mistral",
    "xai",
)

AI_REQUIRED_TERMS = (
    " ai ",
    "artificial intelligence",
    "machine learning",
    "deep learning",
    "generative ai",
    "llm",
    "large language model",
    "computer vision",
    "neural",
    "model",
    "agent",
    "automation",
    "automated",
    "robot",
    "robotic",
    "predictive",
    "defect detection",
    "quality inspection",
    "smart factory",
    "digital twin",
    "virtual try-on",
    "demand forecasting",
    "recommendation",
    "openai",
    "anthropic",
    "deepmind",
    "nvidia",
    "meta ai",
    "microsoft ai",
    "hugging face",
    "mistral",
    "xai",
)


def _keyword_hits(text: str) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    for term, weight in HIGH_SIGNAL_TERMS.items():
        if re.search(rf"\b{re.escape(term)}\b", text):
            score += weight
            reasons.append(term)
    return score, reasons


def is_ai_related(article: Article) -> bool:
    if article.category == "research" or article.source_name.casefold().startswith("arxiv"):
        return False
    text = f" {article.title} {article.summary} {article.source_name} ".casefold()
    if article.category in {"general_ai", "open_source"}:
        return True
    return any(term in text for term in AI_REQUIRED_TERMS) or bool(re.search(r"\bai(?:[-\s]|$)", text))


def rank_article(article: Article) -> RankedArticle:
    text = f"{article.title} {article.summary}".casefold()
    score = CATEGORY_BOOSTS.get(article.category, 0)
    reasons = [article.category]

    keyword_score, keyword_reasons = _keyword_hits(text)
    score += keyword_score
    reasons.extend(keyword_reasons)

    if article.category == "general_ai" and any(company in text for company in GENERAL_AI_COMPANIES):
        score += 12
        reasons.append("major AI company")

    hours_old = max(
        0,
        (datetime.now(timezone.utc) - article.published_at).total_seconds() / 3600,
    )
    if hours_old <= 12:
        score += 12
        reasons.append("fresh")
    elif hours_old <= 24:
        score += 8
        reasons.append("recent")

    if any(word in text for word in ("launch", "release", "introduced", "announced", "partnership")):
        score += 8
        reasons.append("announcement")

    return RankedArticle(article=article, score=min(score, 100), reasons=reasons)


def rank_articles(articles: list[Article]) -> list[RankedArticle]:
    ranked = [rank_article(article) for article in articles if is_ai_related(article)]
    return sorted(ranked, key=lambda item: (item.score, item.article.published_at), reverse=True)
