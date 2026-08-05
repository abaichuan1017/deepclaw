"""Drift test: every env var read by voice_agent_server.py must be documented
in .env.example as an active (non-comment) assignment.

Deliberately avoids importing deepclaw.voice_agent_server (which would
construct a FastAPI app and have other import-time side effects); both
files are read and parsed as plain text instead.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
SERVER_SOURCE = REPO_ROOT / "deepclaw" / "voice_agent_server.py"
ENV_EXAMPLE = REPO_ROOT / ".env.example"

GETENV_RE = re.compile(r"""os\.getenv\(\s*["']([A-Z0-9_]+)["']""")
ACTIVE_ASSIGNMENT_RE = re.compile(r"""^([A-Z0-9_]+)=""", re.MULTILINE)


def test_all_server_env_vars_documented_in_env_example():
    server_text = SERVER_SOURCE.read_text()
    env_example_text = ENV_EXAMPLE.read_text()

    server_vars = set(GETENV_RE.findall(server_text))
    documented_vars = set(ACTIVE_ASSIGNMENT_RE.findall(env_example_text))

    missing = server_vars - documented_vars
    assert not missing, (
        f"Environment variables read by {SERVER_SOURCE.name} but not "
        f"documented as active assignments in {ENV_EXAMPLE.name}: "
        f"{sorted(missing)}"
    )
