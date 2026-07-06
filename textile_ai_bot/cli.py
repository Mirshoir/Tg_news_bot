from __future__ import annotations

import argparse
import asyncio
import logging
import signal

from textile_ai_bot.ai import BriefGenerator
from textile_ai_bot.bot import CommandBot
from textile_ai_bot.collector import collect_articles
from textile_ai_bot.config import load_settings
from textile_ai_bot.dedupe import deduplicate_articles
from textile_ai_bot.formatting import telegram_post
from textile_ai_bot.health import HealthServer
from textile_ai_bot.publisher import TelegramPublisher, _fetch_article_image, publish_pending
from textile_ai_bot.ranker import is_ai_related, rank_articles
from textile_ai_bot.scheduler import build_scheduler
from textile_ai_bot.service import collect_and_store
from textile_ai_bot.sources import DEFAULT_SOURCES
from textile_ai_bot.storage import NewsStore
from textile_ai_bot.telegram_setup import fetch_recent_chat_ids


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Milana Premium AI and textile news bot")
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect = subparsers.add_parser("collect", help="Collect and store articles")
    collect.add_argument("--dry-run", action="store_true", help="Print counts without publishing")

    subparsers.add_parser("post-once", help="Collect and publish one briefing batch")
    subparsers.add_parser("preview", help="Preview the next Telegram post without sending")
    subparsers.add_parser("run", help="Run Telegram command bot and scheduled posting")
    subparsers.add_parser("chat-ids", help="Print recent Telegram chat IDs from getUpdates")
    return parser


async def async_main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    args = build_parser().parse_args()
    settings = load_settings()

    if args.command == "collect":
        if args.dry_run:
            articles = await collect_articles(DEFAULT_SOURCES, settings.collection_lookback_hours)
            unique = deduplicate_articles(articles)
            ranked = rank_articles(unique)
            print(f"Collected unique articles: {len(unique)}")
            print("Top ranked articles:")
            for item in ranked[:5]:
                print(f"- {item.score:>3} {item.article.title} ({item.article.source_name})")
            return

    store = NewsStore(settings.database_path)
    await store.init()

    if args.command == "collect":
        unique, inserted = await collect_and_store(settings, store)
        print(f"Collected unique articles: {unique}")
        print(f"New articles stored: {inserted}")

    if args.command == "post-once":
        if not settings.telegram_enabled:
            raise SystemExit("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required")
        await collect_and_store(settings, store)
        publisher = TelegramPublisher(settings.telegram_bot_token, settings.telegram_chat_id)
        brief_generator = BriefGenerator(settings.openai_api_key, settings.openai_model)
        sent = await publish_pending(
            store,
            publisher,
            brief_generator,
            limit=settings.max_daily_posts,
            min_score=settings.min_importance_score,
        )
        print(f"Published posts: {sent}")
        return

    if args.command == "preview":
        await collect_and_store(settings, store)
        articles = [
            article
            for article in await store.unposted(limit=20, min_score=0)
            if is_ai_related(article)
        ]
        if not articles:
            print("No articles available to preview.")
            return
        brief_generator = BriefGenerator(settings.openai_api_key, settings.openai_model)
        brief = brief_generator.generate(articles[0])
        print(telegram_post(articles[0], brief))
        image_url = articles[0].image_url or await _fetch_article_image(articles[0].url)
        print(f"\nImage URL: {image_url or 'none'}")
        return

    if args.command == "chat-ids":
        if not settings.telegram_bot_token:
            raise SystemExit("TELEGRAM_BOT_TOKEN is required")
        try:
            chats = await fetch_recent_chat_ids(settings.telegram_bot_token)
        except RuntimeError as exc:
            raise SystemExit(str(exc)) from exc
        if not chats:
            print("No recent chats found. Send a message in the group, then run this again.")
            return
        for chat_id, chat_type, name in chats:
            print(f"{chat_id} | {chat_type} | {name}")
        return

    if args.command == "run":
        if not settings.telegram_bot_token:
            raise SystemExit("TELEGRAM_BOT_TOKEN is required")

        publisher = TelegramPublisher(settings.telegram_bot_token, settings.telegram_chat_id or "0")
        brief_generator = BriefGenerator(settings.openai_api_key, settings.openai_model)
        scheduler = None
        if settings.telegram_chat_id:
            scheduler = build_scheduler(settings, store, publisher, brief_generator)
        command_bot = CommandBot(settings, store, publisher, brief_generator)
        app = command_bot.build_application()
        health_server = HealthServer(settings.health_host, settings.health_port)

        if scheduler:
            scheduler.start()
        await health_server.start()
        await app.initialize()
        await app.start()
        await app.updater.start_polling()

        stop_event = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop_event.set)

        await stop_event.wait()
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        await health_server.stop()
        if scheduler:
            scheduler.shutdown(wait=False)


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
