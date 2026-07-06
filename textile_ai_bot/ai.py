from __future__ import annotations

import json
import logging

from openai import OpenAI

from textile_ai_bot.models import Article, IntelligenceBrief
from textile_ai_bot.text_utils import clean_text

LOGGER = logging.getLogger(__name__)

SYSTEM_INSTRUCTIONS = """
You rewrite news for a Telegram channel.
Write only the news itself in Russian and Uzbek.
Keep it short, neutral, factual, and easy to read.
Do not add analysis, business advice, "why it matters", opportunities, highlights, or explanations.
Keep Russian and Uzbek natural, clear, and professional.
Return only valid JSON with this shape:
{
  "title_ru": "...",
  "title_uz": "...",
  "summary_ru": "...",
  "summary_uz": "..."
}
"""


class BriefGenerator:
    def __init__(self, api_key: str, model: str) -> None:
        self.client = OpenAI(api_key=api_key) if api_key else None
        self.model = model

    def generate(self, article: Article) -> IntelligenceBrief:
        if not self.client:
            return fallback_brief(article)

        prompt = f"""
Article title: {article.title}
Source: {article.source_name}
Category: {article.category}
URL: {article.url}
Article excerpt:
{clean_text(article.summary, limit=3000)}
"""
        try:
            response = self.client.responses.create(
                model=self.model,
                instructions=SYSTEM_INSTRUCTIONS,
                input=prompt,
            )
            payload = json.loads(response.output_text)
            return _brief_from_payload(payload, article)
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("OpenAI brief generation failed, using fallback: %s", exc)
            return fallback_brief(article)


def _brief_from_payload(payload: dict, article: Article) -> IntelligenceBrief:
    return IntelligenceBrief(
        title_ru=str(payload.get("title_ru") or article.title),
        title_uz=str(payload.get("title_uz") or article.title),
        summary_ru=clean_text(str(payload.get("summary_ru") or article.summary or article.title), limit=320),
        summary_uz=clean_text(str(payload.get("summary_uz") or article.summary or article.title), limit=320),
        highlights_ru=_list(payload.get("highlights_ru")),
        highlights_uz=_list(payload.get("highlights_uz")),
        why_it_matters_ru="",
        why_it_matters_uz="",
        milana_opportunity_ru="",
        milana_opportunity_uz="",
    )


def _list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()][:4]
    return []


def fallback_brief(article: Article) -> IntelligenceBrief:
    short_summary = clean_text(article.summary or article.title, limit=500)
    return IntelligenceBrief(
        title_ru=article.title,
        title_uz=article.title,
        summary_ru=short_summary,
        summary_uz=short_summary,
        highlights_ru=[],
        highlights_uz=[],
        why_it_matters_ru="",
        why_it_matters_uz="",
        milana_opportunity_ru="",
        milana_opportunity_uz="",
    )
