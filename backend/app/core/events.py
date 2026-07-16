"""Realtime event bus and WebSocket fan out.

Default: an in process asyncio pub/sub, which makes realtime work with zero
external dependencies and in tests, and is ideal for the single workstation
deployment. Optional: when a Redis URL is configured, published events are also
mirrored through Redis pub/sub so that every API replica delivers them, which
supports horizontal scaling. Each process tags its events with an origin token
and ignores its own echoes to avoid duplicate delivery.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from collections import defaultdict
from typing import Any

from app.core.config import get_settings

_ORIGIN = uuid.uuid4().hex
_GLOBAL = "forevi:events"


class EventBus:
    def __init__(self) -> None:
        self._subs: dict[str, set[asyncio.Queue]] = defaultdict(set)
        self._redis = None  # set by start_redis_bridge

    def _deliver_local(self, channel: str, data: str) -> None:
        for q in list(self._subs.get(channel, ())):
            try:
                q.put_nowait(data)
            except asyncio.QueueFull:
                pass

    async def publish(self, channel: str, message: dict[str, Any]) -> None:
        data = json.dumps(message)
        self._deliver_local(channel, data)
        if self._redis is not None:
            try:
                await self._redis.publish(_GLOBAL, json.dumps(
                    {"origin": _ORIGIN, "channel": channel, "data": data}))
            except Exception:
                pass

    def subscribe(self, channel: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self._subs[channel].add(q)
        return q

    def unsubscribe(self, channel: str, q: asyncio.Queue) -> None:
        self._subs.get(channel, set()).discard(q)


bus = EventBus()


async def start_redis_bridge() -> None:
    """Attach Redis pub/sub if configured. Safe to call when Redis is absent."""
    url = get_settings().redis_url
    if not url:
        return
    try:
        import redis.asyncio as aioredis  # type: ignore
    except Exception:
        return
    client = aioredis.from_url(url, encoding="utf-8", decode_responses=True)
    bus._redis = client
    pubsub = client.pubsub()
    await pubsub.subscribe(_GLOBAL)

    async def listen():
        async for msg in pubsub.listen():
            if msg.get("type") != "message":
                continue
            try:
                env = json.loads(msg["data"])
            except Exception:
                continue
            if env.get("origin") == _ORIGIN:
                continue  # ignore our own echo
            bus._deliver_local(env["channel"], env["data"])

    asyncio.create_task(listen())


def user_channel(user_id: str) -> str:
    return f"user:{user_id}"


def case_channel(case_id: str) -> str:
    return f"case:{case_id}"
