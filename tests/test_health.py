from fastapi.testclient import TestClient

from deepclaw.voice_agent_server import app

client = TestClient(app)


def test_health_returns_ok_with_expected_top_level_keys():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert set(["status", "service", "provider", "credentials"]) <= set(body.keys())
    assert body["status"] == "ok"
    assert body["service"] == "deepclaw-voice-agent"


def test_health_reports_twilio_provider(monkeypatch):
    monkeypatch.setenv("VOICE_PROVIDER", "twilio")
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["provider"] == "twilio"


def test_health_reports_telnyx_provider(monkeypatch):
    monkeypatch.setenv("VOICE_PROVIDER", "telnyx")
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["provider"] == "telnyx"


def test_health_does_not_leak_credential_values(monkeypatch):
    secrets = {
        "DEEPGRAM_API_KEY": "fake-secret-do-not-leak-deepgram_api_key",
        "TWILIO_ACCOUNT_SID": "fake-secret-do-not-leak-twilio_account_sid",
        "TWILIO_AUTH_TOKEN": "fake-secret-do-not-leak-twilio_auth_token",
        "TELNYX_API_KEY": "fake-secret-do-not-leak-telnyx_api_key",
        "OPENCLAW_GATEWAY_TOKEN": "fake-secret-do-not-leak-openclaw_gateway_token",
    }
    for name, value in secrets.items():
        monkeypatch.setenv(name, value)

    r = client.get("/health")
    assert r.status_code == 200

    for value in secrets.values():
        assert value not in r.text

    body = r.json()
    assert body["credentials"]["deepgram_api_key_set"] is True
    assert body["credentials"]["openclaw_gateway_token_set"] is True


def test_health_credential_flags_reflect_unset_env(monkeypatch):
    for name in (
        "DEEPGRAM_API_KEY",
        "OPENCLAW_GATEWAY_TOKEN",
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "TELNYX_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("VOICE_PROVIDER", "twilio")

    r = client.get("/health")
    body = r.json()
    assert body["credentials"]["deepgram_api_key_set"] is False
    assert body["credentials"]["openclaw_gateway_token_set"] is False
    assert body["credentials"]["twilio_account_sid_set"] is False
    assert body["credentials"]["twilio_auth_token_set"] is False


def test_health_includes_twilio_specific_credentials_when_twilio_provider(monkeypatch):
    monkeypatch.setenv("VOICE_PROVIDER", "twilio")
    r = client.get("/health")
    credentials = r.json()["credentials"]
    assert "twilio_account_sid_set" in credentials
    assert "twilio_auth_token_set" in credentials
    assert "telnyx_api_key_set" not in credentials


def test_health_includes_telnyx_specific_credentials_when_telnyx_provider(monkeypatch):
    monkeypatch.setenv("VOICE_PROVIDER", "telnyx")
    r = client.get("/health")
    credentials = r.json()["credentials"]
    assert "telnyx_api_key_set" in credentials
    assert "twilio_account_sid_set" not in credentials
    assert "twilio_auth_token_set" not in credentials
