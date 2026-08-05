import asyncio
import hashlib
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from deepclaw.voice_agent_server import app

client = TestClient(app)

RAW_PHONE_NUMBER = "+15551234567"


def _make_fake_deepgram_ws():
    """A stand-in for the `websockets.connect(...)` result that never
    produces real audio/events, so background tasks just idle until the
    endpoint cancels them during cleanup."""
    ws = AsyncMock()

    async def _recv():
        # Block "forever" (until the task is cancelled by the endpoint's
        # finally block) so receive_from_deepgram never raises or spins.
        await asyncio.sleep(3600)

    ws.recv = _recv
    ws.send = AsyncMock(return_value=None)
    ws.close = AsyncMock(return_value=None)
    return ws


class _FakeHTTPXResponse:
    status_code = 200
    content = b"{}"


class _FakeHTTPXClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def post(self, *args, **kwargs):
        return _FakeHTTPXResponse()


def test_twilio_call_lifecycle_is_logged_with_hashed_number(caplog):
    caplog.set_level("INFO")
    fake_ws = _make_fake_deepgram_ws()

    with patch(
        "deepclaw.voice_agent_server.websockets.connect",
        new=AsyncMock(return_value=fake_ws),
    ):
        r = client.post(
            "/twilio/incoming",
            data={"From": RAW_PHONE_NUMBER, "CallSid": "CA_twilio_test_123"},
        )
        assert r.status_code == 200

        with client.websocket_connect("/twilio/media") as ws:
            ws.send_json({"event": "connected"})
            ws.send_json(
                {
                    "event": "start",
                    "streamSid": "MZ_test_stream",
                    "start": {
                        "callSid": "CA_twilio_test_123",
                        "streamSid": "MZ_test_stream",
                    },
                }
            )
            ws.send_json({"event": "stop"})

    expected_hash = hashlib.sha256(RAW_PHONE_NUMBER.encode("utf-8")).hexdigest()[:16]

    assert "Call started: provider=twilio call_id=CA_twilio_test_123" in caplog.text
    assert "Call connected: provider=twilio call_id=CA_twilio_test_123" in caplog.text
    assert "Call ended: provider=twilio call_id=CA_twilio_test_123" in caplog.text
    assert expected_hash in caplog.text

    end_lines = [
        line for line in caplog.text.splitlines() if "Call ended: provider=twilio" in line
    ]
    assert end_lines, "expected a call-end log line"
    assert "duration=" in end_lines[0]


def test_telnyx_call_lifecycle_is_logged_with_hashed_number(caplog):
    caplog.set_level("INFO")
    fake_ws = _make_fake_deepgram_ws()

    with patch(
        "deepclaw.voice_agent_server.websockets.connect",
        new=AsyncMock(return_value=fake_ws),
    ), patch(
        "deepclaw.voice_agent_server.httpx.AsyncClient",
        return_value=_FakeHTTPXClient(),
    ):
        r = client.post(
            "/telnyx/webhook",
            json={
                "data": {
                    "event_type": "call.initiated",
                    "payload": {
                        "call_control_id": "v3:telnyx_test_abc",
                        "from": RAW_PHONE_NUMBER,
                    },
                }
            },
        )
        assert r.status_code == 200

        with client.websocket_connect("/telnyx/media") as ws:
            ws.send_json({"event": "connected"})
            ws.send_json(
                {
                    "event": "start",
                    "start": {"call_control_id": "v3:telnyx_test_abc"},
                    "stream_id": "stream_test_abc",
                }
            )

            r = client.post(
                "/telnyx/webhook",
                json={
                    "data": {
                        "event_type": "call.answered",
                        "payload": {"call_control_id": "v3:telnyx_test_abc"},
                    }
                },
            )
            assert r.status_code == 200

            r = client.post(
                "/telnyx/webhook",
                json={
                    "data": {
                        "event_type": "call.hangup",
                        "payload": {"call_control_id": "v3:telnyx_test_abc"},
                    }
                },
            )
            assert r.status_code == 200

            ws.send_json({"event": "stop"})

    expected_hash = hashlib.sha256(RAW_PHONE_NUMBER.encode("utf-8")).hexdigest()[:16]

    assert "Call started: provider=telnyx call_id=v3:telnyx_test_abc" in caplog.text
    assert "Call connected: provider=telnyx call_id=v3:telnyx_test_abc" in caplog.text
    assert "Call ended: provider=telnyx call_id=v3:telnyx_test_abc" in caplog.text
    assert expected_hash in caplog.text

    end_lines = [
        line for line in caplog.text.splitlines() if "Call ended: provider=telnyx" in line
    ]
    assert end_lines, "expected a call-end log line"
    assert "duration=" in end_lines[0]


def test_raw_phone_number_never_appears_in_logs_across_either_provider(caplog):
    caplog.set_level("INFO")
    fake_ws = _make_fake_deepgram_ws()

    with patch(
        "deepclaw.voice_agent_server.websockets.connect",
        new=AsyncMock(return_value=fake_ws),
    ), patch(
        "deepclaw.voice_agent_server.httpx.AsyncClient",
        return_value=_FakeHTTPXClient(),
    ):
        # Twilio lifecycle
        client.post(
            "/twilio/incoming",
            data={"From": RAW_PHONE_NUMBER, "CallSid": "CA_privacy_test"},
        )
        with client.websocket_connect("/twilio/media") as ws:
            ws.send_json({"event": "connected"})
            ws.send_json(
                {
                    "event": "start",
                    "streamSid": "MZ_privacy_stream",
                    "start": {
                        "callSid": "CA_privacy_test",
                        "streamSid": "MZ_privacy_stream",
                    },
                }
            )
            ws.send_json({"event": "stop"})

        # Telnyx lifecycle
        client.post(
            "/telnyx/webhook",
            json={
                "data": {
                    "event_type": "call.initiated",
                    "payload": {
                        "call_control_id": "v3:privacy_test",
                        "from": RAW_PHONE_NUMBER,
                    },
                }
            },
        )
        client.post(
            "/telnyx/webhook",
            json={
                "data": {
                    "event_type": "call.answered",
                    "payload": {"call_control_id": "v3:privacy_test"},
                }
            },
        )
        client.post(
            "/telnyx/webhook",
            json={
                "data": {
                    "event_type": "call.hangup",
                    "payload": {"call_control_id": "v3:privacy_test"},
                }
            },
        )

    # The raw number must never leak into logs...
    assert RAW_PHONE_NUMBER not in caplog.text
    # ...but lifecycle logging did actually happen (so this isn't passing
    # merely because nothing was logged).
    assert "Call started: provider=twilio" in caplog.text
    assert "Call started: provider=telnyx" in caplog.text
