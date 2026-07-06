from __future__ import annotations

import re
from hashlib import sha256
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from textile_ai_bot.models import Article

TRACKING_PREFIXES = ("utm_",)
TRACKING_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid"}


def canonical_url(url: str) -> str:
    parsed = urlsplit(url.strip())
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=False)
        if key not in TRACKING_KEYS and not key.startswith(TRACKING_PREFIXES)
    ]
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            path,
            urlencode(query),
            "",
        )
    )


def normalize_title(title: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", title.casefold())
    return re.sub(r"\s+", " ", normalized).strip()


def article_fingerprint(article: Article) -> str:
    identity = canonical_url(article.url) or normalize_title(article.title)
    return sha256(identity.encode("utf-8")).hexdigest()


def deduplicate_articles(articles: list[Article]) -> list[Article]:
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    unique: list[Article] = []

    for article in sorted(articles, key=lambda item: item.published_at, reverse=True):
        url_key = canonical_url(article.url)
        title_key = normalize_title(article.title)
        if url_key in seen_urls or title_key in seen_titles:
            continue
        seen_urls.add(url_key)
        seen_titles.add(title_key)
        unique.append(article)

    return unique
