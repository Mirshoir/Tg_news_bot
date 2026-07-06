from __future__ import annotations

import httpx


async def fetch_recent_chat_ids(token: str) -> list[tuple[int, str, str]]:
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(f"https://api.telegram.org/bot{token}/getUpdates")
    payload = response.json()
    if not payload.get("ok"):
        description = payload.get("description", "Unknown Telegram API error")
        raise RuntimeError(str(description))

    chats: list[tuple[int, str, str]] = []
    for update in payload.get("result", []):
        message = (
            update.get("message")
            or update.get("edited_message")
            or update.get("channel_post")
            or {}
        )
        chat = message.get("chat") or {}
        chat_id = chat.get("id")
        if chat_id is None:
            continue
        item = (
            int(chat_id),
            str(chat.get("type") or ""),
            str(chat.get("title") or chat.get("username") or chat.get("first_name") or ""),
        )
        if item not in chats:
            chats.append(item)
    return chats
