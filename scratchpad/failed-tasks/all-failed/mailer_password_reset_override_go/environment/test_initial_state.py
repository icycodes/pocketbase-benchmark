import os
import shutil
import socket
import subprocess
import time

import pytest
import requests

PROJECT_DIR = "/home/user/myapp"
MAILPIT_API = "http://localhost:8025"
MAILPIT_SMTP_HOST = "localhost"
MAILPIT_SMTP_PORT = 1025


def _port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _ensure_mailpit_running() -> None:
    """Start Mailpit if it is not already running."""
    if _port_open("127.0.0.1", 1025) and _port_open("127.0.0.1", 8025):
        return
    assert shutil.which("mailpit") is not None, "mailpit binary not found in PATH."
    log = open("/tmp/mailpit.log", "ab")
    subprocess.Popen(
        ["mailpit", "--smtp", "0.0.0.0:1025", "--listen", "0.0.0.0:8025"],
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    deadline = time.time() + 15.0
    while time.time() < deadline:
        if _port_open("127.0.0.1", 1025) and _port_open("127.0.0.1", 8025):
            return
        time.sleep(0.3)
    raise AssertionError("Mailpit did not start within 15 seconds.")


def test_go_toolchain_available():
    assert shutil.which("go") is not None, "go toolchain not found in PATH."


def test_mailpit_binary_available():
    assert shutil.which("mailpit") is not None, "mailpit binary not found in PATH."


def test_project_dir_exists():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} does not exist."


def test_mailpit_smtp_reachable():
    _ensure_mailpit_running()
    assert _port_open(MAILPIT_SMTP_HOST, MAILPIT_SMTP_PORT), (
        f"Mailpit SMTP port {MAILPIT_SMTP_PORT} is not reachable on {MAILPIT_SMTP_HOST}."
    )


def test_mailpit_api_reachable():
    _ensure_mailpit_running()
    resp = requests.get(f"{MAILPIT_API}/api/v1/messages", timeout=5)
    assert resp.status_code == 200, (
        f"Mailpit API did not return 200 from /api/v1/messages, got {resp.status_code}."
    )
    body = resp.json()
    assert "messages" in body, "Mailpit API response missing 'messages' field."


def test_required_env_vars_present():
    # Sanity check that the verifier/agent envs were injected.
    for key in ("TEST_USER_EMAIL", "TEST_USER_NAME", "SUPERUSER_EMAIL", "SUPERUSER_PASSWORD"):
        assert os.environ.get(key), f"Required environment variable {key} is not set."
