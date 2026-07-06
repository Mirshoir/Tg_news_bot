from __future__ import annotations

import html

from textile_ai_bot.models import Article, IntelligenceBrief
from textile_ai_bot.text_utils import clean_text


def telegram_post(article: Article, brief: IntelligenceBrief) -> str:
    title_ru = clean_text(brief.title_ru or article.title, limit=140)
    title_uz = clean_text(brief.title_uz or article.title, limit=140)
    summary_ru = clean_text(brief.summary_ru or article.summary, limit=320)
    summary_uz = clean_text(brief.summary_uz or article.summary, limit=320)
    return "\n".join(
        part
        for part in [
            "<b>Milana news</b>",
            "",
            "🇷🇺 <b>Русский</b>",
            f"<b>{html.escape(title_ru)}</b>",
            html.escape(summary_ru),
            "",
            "🇺🇿 <b>O'zbekcha</b>",
            f"<b>{html.escape(title_uz)}</b>",
            html.escape(summary_uz),
            "",
            f"🔗 <b>Источник / Manba:</b> <a href=\"{html.escape(article.url)}\">{html.escape(article.source_name)}</a>",
        ]
        if part
    )


def article_list(title: str, articles: list[Article]) -> str:
    if not articles:
        return f"<b>{html.escape(title)}</b>\nNo matching articles found."
    lines = [f"<b>{html.escape(title)}</b>"]
    for index, article in enumerate(articles, start=1):
        lines.append(
            f"{index}. <a href=\"{html.escape(article.url)}\">{html.escape(article.title)}</a> "
            f"({html.escape(article.source_name)})"
        )
    return "\n".join(lines)
