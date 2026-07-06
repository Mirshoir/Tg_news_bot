from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

LOGGER = logging.getLogger(__name__)


class HealthServer:
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self._server: asyncio.AbstractServer | None = None

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._handle, self.host, self.port)
        LOGGER.info("Health server started on %s:%s", self.host, self.port)

    async def stop(self) -> None:
        if not self._server:
            return
        self._server.close()
        await self._server.wait_closed()

    async def _handle(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        request_line = await reader.readline()
        parts = request_line.decode("latin-1", errors="ignore").split()
        method = parts[0] if len(parts) >= 1 else ""
        path = parts[1] if len(parts) >= 2 else ""

        while True:
            line = await reader.readline()
            if line in {b"\r\n", b"\n", b""}:
                break

        if method != "GET" or path != "/health":
            await self._write_json(writer, 404, {"ok": False, "error": "not found"})
            return

        await self._write_json(
            writer,
            200,
            {
                "ok": True,
                "service": "kotiba-tg-news",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def _write_json(
        self,
        writer: asyncio.StreamWriter,
        status: int,
        payload: dict[str, object],
    ) -> None:
        reason = "OK" if status == 200 else "Not Found"
        body = json.dumps(payload).encode("utf-8")
        writer.write(
            (
                f"HTTP/1.1 {status} {reason}\r\n"
                "Content-Type: application/json\r\n"
                f"Content-Length: {len(body)}\r\n"
                "Connection: close\r\n"
                "\r\n"
            ).encode("ascii")
            + body
        )
        await writer.drain()
        writer.close()
        await writer.wait_closed()
