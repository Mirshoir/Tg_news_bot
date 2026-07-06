from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from textile_ai_bot.ai import BriefGenerator
from textile_ai_bot.config import Settings
from textile_ai_bot.formatting import article_list
from textile_ai_bot.publisher import TelegramPublisher, publish_pending
from textile_ai_bot.ranker import is_ai_related
from textile_ai_bot.service import collect_and_store
from textile_ai_bot.storage import NewsStore

LOGGER = logging.getLogger(__name__)


class CommandBot:
    def __init__(
        self,
        settings: Settings,
        store: NewsStore,
        publisher: TelegramPublisher,
        brief_generator: BriefGenerator,
    ) -> None:
        self.settings = settings
        self.store = store
        self.publisher = publisher
        self.brief_generator = brief_generator

    def build_application(self) -> Application:
        app = Application.builder().token(self.settings.telegram_bot_token).build()
        app.add_handler(CommandHandler("today", self.today))
        app.add_handler(CommandHandler("week", self.week))
        app.add_handler(CommandHandler("textile", self.textile))
        app.add_handler(CommandHandler("research", self.research))
        app.add_handler(CommandHandler("openai", self.openai))
        app.add_handler(CommandHandler("fashion", self.fashion))
        app.add_handler(CommandHandler("github", self.github))
        app.add_handler(CommandHandler("search", self.search))
        app.add_handler(CommandHandler(["chatid", "chat_id", "id"], self.chatid))
        app.add_handler(CommandHandler("pause", self.pause))
        app.add_handler(CommandHandler("resume", self.resume))
        app.add_handler(CommandHandler("test", self.test))
        app.add_handler(CommandHandler("settings", self.settings_command))
        app.add_error_handler(self.error_handler)
        return app

    async def today(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await collect_and_store(self.settings, self.store)
        articles = await self.store.recent(days=1, limit=10)
        articles = [article for article in articles if is_ai_related(article)]
        await self._reply(update, article_list("Today | Bugun", articles))

    async def week(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        articles = await self.store.recent(days=7, limit=10)
        articles = [article for article in articles if is_ai_related(article)]
        await self._reply(update, article_list("This Week | Shu hafta", articles))

    async def textile(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self._category(update, "textile", "Textile | Tekstil")

    async def research(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self._category(update, "research", "Research | Tadqiqot")

    async def fashion(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self._category(update, "fashion", "Fashion Tech | Moda texnologiyasi")

    async def github(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self._category(update, "open_source", "Open Source | Ochiq kod")

    async def openai(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        articles = await self.store.search("OpenAI", limit=10)
        articles = [article for article in articles if is_ai_related(article)]
        await self._reply(update, article_list("OpenAI Updates | OpenAI yangiliklari", articles))

    async def search(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = " ".join(context.args).strip()
        if not query:
            await self._reply(update, "Usage: /search defect detection")
            return
        articles = await self.store.search(query, limit=10)
        articles = [article for article in articles if is_ai_related(article)]
        await self._reply(update, article_list(f"Search: {query}", articles))

    async def chatid(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat = update.effective_chat
        if not chat:
            await self._reply(update, "Chat ID not available.")
            return
        await self._reply(update, f"Chat ID: <code>{chat.id}</code>")

    async def pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._is_admin(update):
            return
        await self.store.set_state("paused", "1")
        await self._reply(update, "Scheduled posting paused.")

    async def resume(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._is_admin(update):
            return
        await self.store.set_state("paused", "0")
        await self._reply(update, "Scheduled posting resumed.")

    async def test(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._is_admin(update):
            return
        await collect_and_store(self.settings, self.store)
        sent = await publish_pending(
            self.store,
            self.publisher,
            self.brief_generator,
            limit=1,
            min_score=0,
        )
        await self._reply(update, f"Test complete. Posts sent: {sent}")

    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._is_admin(update):
            return
        paused = await self.store.get_state("paused", "0")
        text = (
            "<b>Settings</b>\n"
            f"Timezone: {self.settings.timezone}\n"
            f"Morning: {self.settings.morning_brief_time}\n"
            f"Afternoon: {self.settings.afternoon_update_time}\n"
            f"Min score: {self.settings.min_importance_score}\n"
            f"Max posts: {self.settings.max_daily_posts}\n"
            f"OpenAI: {'enabled' if self.settings.openai_enabled else 'disabled'}\n"
            f"Paused: {'yes' if paused == '1' else 'no'}"
        )
        await self._reply(update, text)

    async def _category(self, update: Update, category: str, title: str) -> None:
        articles = await self.store.recent(days=7, limit=10, category=category)
        articles = [article for article in articles if is_ai_related(article)]
        await self._reply(update, article_list(title, articles))

    async def _is_admin(self, update: Update) -> bool:
        user = update.effective_user
        if not self.settings.admin_user_ids:
            return True
        if user and user.id in self.settings.admin_user_ids:
            return True
        await self._reply(update, "Admin only.")
        return False

    async def _reply(self, update: Update, text: str) -> None:
        if update.effective_message:
            await update.effective_message.reply_text(
                text,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        LOGGER.exception("Telegram command failed: update=%s", update, exc_info=context.error)
