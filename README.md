# AI & Textile Intelligence Telegram Bot

Automated Telegram bot for bilingual Russian and Uzbek AI/textile news updates for the Milana Premium AI Team.

The bot collects trusted RSS/news sources, filters textile and AI topics, removes duplicate stories, ranks importance, optionally generates AI summaries, and publishes concise Telegram posts with:

- Russian summary
- Uzbek summary
- key highlights
- why it matters
- Milana Premium opportunity
- source link

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env`:

```bash
TELEGRAM_BOT_TOKEN=123456:telegram-token
TELEGRAM_CHAT_ID=-1001234567890
OPENAI_API_KEY=sk-...
```

Run a dry collection:

```bash
python -m textile_ai_bot.cli collect --dry-run
```

Post one briefing:

```bash
python -m textile_ai_bot.cli post-once
```

Preview the next post without sending it:

```bash
python -m textile_ai_bot.cli preview
```

Run the scheduler and Telegram command bot:

```bash
python -m textile_ai_bot.cli run
```

Health check:

```bash
curl http://127.0.0.1:8006/health
```

If `/chatid` does not answer during setup, stop the bot with `Ctrl+C`, send any message in the group, then run:

```bash
python -m textile_ai_bot.cli chat-ids
```

## Commands

- `/today` - latest collected stories
- `/week` - best stories from the last 7 days
- `/textile` - textile and manufacturing updates
- `/research` - research papers and technical posts
- `/openai` - OpenAI-related updates
- `/fashion` - fashion technology updates
- `/github` - open-source AI updates
- `/search defect detection` - search local article history
- `/chatid`, `/chat_id`, `/id` - show the current Telegram chat ID
- `/pause` - pause scheduled posting, admin only
- `/resume` - resume scheduled posting, admin only
- `/test` - send a test post, admin only
- `/settings` - show current runtime settings, admin only

## Docker

```bash
docker build -t textile-ai-news-bot .
docker run --env-file .env -v "$PWD/data:/app/data" textile-ai-news-bot
```

## Notes

- OpenAI is optional. Without `OPENAI_API_KEY`, the bot still collects, ranks, deduplicates, and formats simple bilingual posts.
- SQLite is used by default and can be migrated later to PostgreSQL if needed.
- RSS failures are logged and skipped so one broken source does not block the briefing.
- Set `POST_INTERVAL_MINUTES=30` to check and publish fresh AI-related news every 30 minutes. If it is `0`, the morning and afternoon schedule is used.
- `MIN_IMPORTANCE_SCORE=30` is recommended for automatic posting; higher values may collect news but stay quiet.
