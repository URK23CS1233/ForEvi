"""Authenticated WebSocket endpoint for realtime case and user events."""
import asyncio

import jwt as pyjwt
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.events import bus, case_channel, user_channel
from app.core.security import decode_token
from app.db.base import SessionLocal
from app.db.models import Case, Role, User

router = APIRouter(tags=["realtime"])


async def _authenticate(token: str) -> User | None:
    try:
        payload = decode_token(token, "access")
    except pyjwt.InvalidTokenError:
        return None
    async with SessionLocal() as db:
        user = await db.get(User, payload.get("sub", ""))
        return user


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket, token: str = Query(...), case_id: str | None = Query(default=None)):
    user = await _authenticate(token)
    if user is None or user.status.value != "ACTIVE":
        await ws.close(code=4401)
        return

    channels = [user_channel(user.id)]
    if case_id:
        async with SessionLocal() as db:
            case = await db.get(Case, case_id)
            if case and (user.role in {Role.ADMIN, Role.AUDITOR, Role.FORENSIC_ANALYST} or case.owner_id == user.id):
                channels.append(case_channel(case_id))

    await ws.accept()
    queues = [(c, bus.subscribe(c)) for c in channels]
    await ws.send_json({"type": "connected", "channels": channels})

    async def pump(q):
        while True:
            data = await q.get()
            await ws.send_text(data)

    tasks = [asyncio.create_task(pump(q)) for _, q in queues]
    try:
        while True:
            # keep the socket alive; ignore any client message except close
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        for t in tasks:
            t.cancel()
        for c, q in queues:
            bus.unsubscribe(c, q)
