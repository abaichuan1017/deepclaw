"""Subprocess tests for `python -m deepclaw` and `python -m deepclaw doctor`."""

import subprocess
import sys

DEEPGRAM_TEST_VALUE = "deepgram-secret-value-should-never-appear-in-output"

BASE_ENV = {
    "DEEPGRAM_API_KEY": DEEPGRAM_TEST_VALUE,
    "OPENCLAW_GATEWAY_TOKEN": "openclaw-secret-token",
}

TWILIO_ENV = {
    **BASE_ENV,
    "VOICE_PROVIDER": "twilio",
    "TWILIO_ACCOUNT_SID": "twilio-sid",
    "TWILIO_AUTH_TOKEN": "twilio-auth-token",
}

TELNYX_ENV = {
    **BASE_ENV,
    "VOICE_PROVIDER": "telnyx",
    "TELNYX_API_KEY": "telnyx-api-key",
    "TELNYX_PUBLIC_KEY": "telnyx-public-key",
}


def run_deepclaw(env, *args, timeout=10):
    """Run `python -m deepclaw [args]` with a fully controlled environment."""
    minimal_env = {"PATH": "/usr/bin:/bin", "PYTHONPATH": "."}
    minimal_env.update(env)
    return subprocess.run(
        [sys.executable, "-m", "deepclaw", *args],
        env=minimal_env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def test_doctor_exits_zero_for_fully_configured_twilio():
    result = run_deepclaw(TWILIO_ENV, "doctor")
    assert result.returncode == 0, result.stdout + result.stderr


def test_doctor_exits_zero_for_fully_configured_telnyx():
    result = run_deepclaw(TELNYX_ENV, "doctor")
    assert result.returncode == 0, result.stdout + result.stderr


def test_doctor_reports_missing_twilio_variable():
    env = dict(TWILIO_ENV)
    del env["TWILIO_ACCOUNT_SID"]
    result = run_deepclaw(env, "doctor")
    combined = result.stdout + result.stderr
    assert result.returncode != 0
    assert "TWILIO_ACCOUNT_SID" in combined
    assert "MISSING" in combined


def test_doctor_reports_missing_telnyx_variable():
    env = dict(TELNYX_ENV)
    del env["TELNYX_PUBLIC_KEY"]
    result = run_deepclaw(env, "doctor")
    combined = result.stdout + result.stderr
    assert result.returncode != 0
    assert "TELNYX_PUBLIC_KEY" in combined
    assert "MISSING" in combined


def test_doctor_never_prints_credential_values():
    env = dict(TWILIO_ENV)
    result = run_deepclaw(env, "doctor")
    combined = result.stdout + result.stderr
    assert DEEPGRAM_TEST_VALUE not in combined


def test_doctor_never_prints_credential_values_when_missing():
    env = dict(TWILIO_ENV)
    del env["TWILIO_ACCOUNT_SID"]
    result = run_deepclaw(env, "doctor")
    combined = result.stdout + result.stderr
    assert DEEPGRAM_TEST_VALUE not in combined


def test_main_exits_nonzero_with_missing_credentials():
    result = run_deepclaw({}, timeout=10)
    assert result.returncode != 0
