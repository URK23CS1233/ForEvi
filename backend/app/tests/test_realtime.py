"""Realtime bus and WebSocket authentication tests."""
import pytest

from app.core.events import EventBus, bus, case_channel
from app.core.security import create_access_token
from app.api.v1.ws import _authenticate

pytestmark = pytest.mark.asyncio


async def test_bus_publish_subscribe():
    b = EventBus()
    q = b.subscribe("case:1")
    await b.publish("case:1", {"type": "ping", "n": 1})
    msg = await q.get()
    assert '"ping"' in msg and '"n": 1' in msg


async def test_bus_unsubscribe_stops_delivery():
    b = EventBus()
    q = b.subscribe("c")
    b.unsubscribe("c", q)
    await b.publish("c", {"x": 1})
    assert q.empty()


async def test_ws_authenticate_valid_and_invalid(client):
    from app.tests.conftest import register_and_activate
    tok = await register_and_activate(client, "ws@nia.gov.in", "INVESTIGATING_OFFICER")
    # decode the user id from a fresh access token path: reuse the returned token
    user = await _authenticate(tok["access_token"])
    assert user is not None and user.email == "ws@nia.gov.in"
    assert await _authenticate("not-a-token") is None
