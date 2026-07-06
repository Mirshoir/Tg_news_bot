from __future__ import annotations

from textile_ai_bot.models import NewsSource


DEFAULT_SOURCES: tuple[NewsSource, ...] = (
    NewsSource("Textile World", "https://www.textileworld.com/feed/", "textile", 88),
    NewsSource("Fibre2Fashion", "https://www.fibre2fashion.com/news", "textile", 86, kind="html", link_patterns=("/news/",)),
    NewsSource("Apparel Resources", "https://apparelresources.com/feed/", "textile", 80),
    NewsSource("Textile Today", "https://www.textiletoday.com.bd/feed/", "textile", 78),
    NewsSource("FashionUnited", "https://fashionunited.com/", "fashion", 76, kind="html", link_patterns=("/news/",)),
    NewsSource("OpenAI", "https://openai.com/news/rss.xml", "general_ai", 92),
    NewsSource("Anthropic", "https://www.anthropic.com/news", "general_ai", 90, kind="html", link_patterns=("/news/",)),
    NewsSource("Google DeepMind", "https://deepmind.google/blog/rss.xml", "general_ai", 88),
    NewsSource("NVIDIA AI Blog", "https://blogs.nvidia.com/feed/", "general_ai", 86),
    NewsSource("Microsoft AI Platform", "https://techcommunity.microsoft.com/t5/s/gxcuf89792/rss/board?board.id=AIPlatformBlog", "general_ai", 84),
    NewsSource("Hugging Face Blog", "https://huggingface.co/blog/feed.xml", "open_source", 82),
    NewsSource("arXiv AI", "https://export.arxiv.org/rss/cs.AI", "research", 78),
    NewsSource("arXiv CV", "https://export.arxiv.org/rss/cs.CV", "research", 80),
)
