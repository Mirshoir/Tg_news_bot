from __future__ import annotations

import html
import re

from bs4 import BeautifulSoup


def clean_text(value: str, *, limit: int | None = None) -> str:
    text = html.unescape(value or "")
    text = BeautifulSoup(text, "html.parser").get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s*\[…\]\s*$", "", text).strip()
    if limit and len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0].rstrip(".,;:") + "..."
    return text
