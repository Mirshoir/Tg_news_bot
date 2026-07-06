from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import aiosqlite

from textile_ai_bot.dedupe import article_fingerprint, canonical_url
from textile_ai_bot.models import Article, RankedArticle


class NewsStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    async def init(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.database_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS articles (
                    fingerprint TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    canonical_url TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    category TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    image_url TEXT NOT NULL DEFAULT '',
                    score INTEGER NOT NULL DEFAULT 0,
                    published_at TEXT NOT NULL,
                    posted_at TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            columns = await db.execute_fetchall("PRAGMA table_info(articles)")
            column_names = {str(column[1]) for column in columns}
            if "image_url" not in column_names:
                await db.execute("ALTER TABLE articles ADD COLUMN image_url TEXT NOT NULL DEFAULT ''")
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            await db.commit()

    async def upsert_ranked(self, ranked_articles: list[RankedArticle]) -> int:
        now = datetime.now(timezone.utc).isoformat()
        inserted = 0
        async with aiosqlite.connect(self.database_path) as db:
            for ranked in ranked_articles:
                article = ranked.article
                cursor = await db.execute(
                    """
                    INSERT OR IGNORE INTO articles (
                        fingerprint, title, url, canonical_url, source_name, source_url,
                        category, summary, image_url, score, published_at, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        article_fingerprint(article),
                        article.title,
                        article.url,
                        canonical_url(article.url),
                        article.source_name,
                        article.source_url,
                        article.category,
                        article.summary,
                        article.image_url,
                        ranked.score,
                        article.published_at.isoformat(),
                        now,
                    ),
                )
                inserted += cursor.rowcount
                await db.execute(
                    """
                    UPDATE articles
                    SET score = MAX(score, ?),
                        summary = CASE WHEN summary = '' THEN ? ELSE summary END,
                        image_url = CASE WHEN image_url = '' THEN ? ELSE image_url END
                    WHERE fingerprint = ?
                    """,
                    (ranked.score, article.summary, article.image_url, article_fingerprint(article)),
                )
            await db.commit()
        return inserted

    async def unposted(self, limit: int, min_score: int) -> list[Article]:
        async with aiosqlite.connect(self.database_path) as db:
            rows = await db.execute_fetchall(
                """
                SELECT source_name, source_url, title, url, category, summary, image_url, published_at
                FROM articles
                WHERE posted_at IS NULL AND score >= ?
                ORDER BY score DESC, published_at DESC
                LIMIT ?
                """,
                (min_score, limit),
            )
        return [_row_to_article(row) for row in rows]

    async def mark_posted(self, article: Article) -> None:
        async with aiosqlite.connect(self.database_path) as db:
            await db.execute(
                "UPDATE articles SET posted_at = ? WHERE fingerprint = ?",
                (datetime.now(timezone.utc).isoformat(), article_fingerprint(article)),
            )
            await db.commit()

    async def recent(self, days: int, limit: int, category: str | None = None) -> list[Article]:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        query = """
            SELECT source_name, source_url, title, url, category, summary, image_url, published_at
            FROM articles
            WHERE published_at >= ?
        """
        params: list[object] = [since.isoformat()]
        if category:
            query += " AND category = ?"
            params.append(category)
        query += " ORDER BY score DESC, published_at DESC LIMIT ?"
        params.append(limit)

        async with aiosqlite.connect(self.database_path) as db:
            rows = await db.execute_fetchall(query, params)
        return [_row_to_article(row) for row in rows]

    async def search(self, query: str, limit: int = 10) -> list[Article]:
        pattern = f"%{query}%"
        async with aiosqlite.connect(self.database_path) as db:
            rows = await db.execute_fetchall(
                """
                SELECT source_name, source_url, title, url, category, summary, image_url, published_at
                FROM articles
                WHERE title LIKE ? OR summary LIKE ?
                ORDER BY score DESC, published_at DESC
                LIMIT ?
                """,
                (pattern, pattern, limit),
            )
        return [_row_to_article(row) for row in rows]

    async def get_state(self, key: str, default: str = "") -> str:
        async with aiosqlite.connect(self.database_path) as db:
            rows = await db.execute_fetchall("SELECT value FROM state WHERE key = ?", (key,))
        row = rows[0] if rows else None
        return str(row[0]) if row else default

    async def set_state(self, key: str, value: str) -> None:
        async with aiosqlite.connect(self.database_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO state (key, value) VALUES (?, ?)",
                (key, value),
            )
            await db.commit()


def _row_to_article(row: tuple) -> Article:
    published_at = datetime.fromisoformat(row[7])
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)
    return Article(
        source_name=row[0],
        source_url=row[1],
        title=row[2],
        url=row[3],
        category=row[4],
        summary=row[5],
        image_url=row[6],
        published_at=published_at,
    )
