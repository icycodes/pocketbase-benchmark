import base64
import json
import os
import re
import socket
import subprocess
import time
from typing import Optional

import pytest
import requests
from xprocess import ProcessStarter

PROJECT_DIR = "/home/user/myapp"
PB_URL = "http://localhost:8090"
MAILPIT_URL = "http://localhost:8025"

TEST_USER_EMAIL = os.environ.get("TEST_USER_EMAIL", "alice@example.com")
TEST_USER_NAME = os.environ.get("TEST_USER_NAME", "Alice")
SUPERUSER_EMAIL = os.environ.get("SUPERUSER_EMAIL", "admin@example.com")
SUPERUSER_PASSWORD = os.environ.get("SUPERUSER_PASSWORD", "SuperSecret123!")

JWT_RE = r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"


def _port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _pb_health_ok() -> bool:
    try:
        r = requests.get(f"{PB_URL}/api/health", timeout=2)
        return r.status_code == 200
    except requests.RequestException:
        return False


@pytest.fixture(scope="session")
def start_pb(xprocess):
    """Ensure the agent's PocketBase Go app is running on :8090."""
    if _pb_health_ok():
        yield
        return

    class Starter(ProcessStarter):
        name = "pb_app"
        args = ["go", "run", ".", "serve", "--http=0.0.0.0:8090"]
        env = os.environ.copy()
        popen_kwargs = {
            "cwd": PROJECT_DIR,
            "text": True,
        }
        timeout = 240
        terminate_on_interrupt = True

        def startup_check(self):
            return _pb_health_ok()

    xprocess.ensure(Starter.name, Starter)
    yield
    info = xprocess.getinfo(Starter.name)
    info.terminate()


def _clear_mailpit() -> None:
    resp = requests.delete(f"{MAILPIT_URL}/api/v1/messages", timeout=10)
    assert resp.status_code in (200, 202), (
        f"Failed to clear Mailpit mailbox: HTTP {resp.status_code} {resp.text}"
    )


def _list_mailpit_messages() -> list:
    resp = requests.get(f"{MAILPIT_URL}/api/v1/messages", timeout=10)
    assert resp.status_code == 200, (
        f"Mailpit /api/v1/messages returned HTTP {resp.status_code}: {resp.text}"
    )
    data = resp.json()
    return data.get("messages", []) or []


def _wait_for_messages(expected: int = 1, timeout: float = 15.0) -> list:
    deadline = time.time() + timeout
    msgs: list = []
    while time.time() < deadline:
        msgs = _list_mailpit_messages()
        if len(msgs) >= expected:
            return msgs
        time.sleep(0.5)
    return msgs


def _get_mailpit_message(message_id: str) -> dict:
    resp = requests.get(f"{MAILPIT_URL}/api/v1/message/{message_id}", timeout=10)
    assert resp.status_code == 200, (
        f"Mailpit /api/v1/message/{message_id} returned HTTP {resp.status_code}: {resp.text}"
    )
    return resp.json()


def _b64url_decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def _decode_jwt_payload(token: str) -> dict:
    parts = token.split(".")
    assert len(parts) == 3, f"Token is not a 3-part JWT: {token!r}"
    payload_bytes = _b64url_decode(parts[1])
    return json.loads(payload_bytes)


def _request_password_reset(email: str) -> requests.Response:
    return requests.post(
        f"{PB_URL}/api/collections/users/request-password-reset",
        json={"email": email},
        timeout=15,
    )


def _superuser_token() -> str:
    resp = requests.post(
        f"{PB_URL}/api/collections/_superusers/auth-with-password",
        json={"identity": SUPERUSER_EMAIL, "password": SUPERUSER_PASSWORD},
        timeout=15,
    )
    assert resp.status_code == 200, (
        f"Superuser auth-with-password failed: HTTP {resp.status_code} {resp.text}"
    )
    return resp.json()["token"]


def _find_user_record_id(token: str, email: str) -> str:
    resp = requests.get(
        f"{PB_URL}/api/collections/users/records",
        params={"filter": f"(email='{email}')"},
        headers={"Authorization": token},
        timeout=15,
    )
    assert resp.status_code == 200, (
        f"Listing users collection failed: HTTP {resp.status_code} {resp.text}"
    )
    items = resp.json().get("items", [])
    assert items, f"Seeded user with email {email} not found in users collection."
    return items[0]["id"]


def _patch_user(token: str, record_id: str, body: dict) -> None:
    resp = requests.patch(
        f"{PB_URL}/api/collections/users/records/{record_id}",
        json=body,
        headers={"Authorization": token},
        timeout=15,
    )
    assert resp.status_code == 200, (
        f"Patching user record {record_id} failed: HTTP {resp.status_code} {resp.text}"
    )


def test_pocketbase_reachable(start_pb):
    assert _pb_health_ok(), "PocketBase /api/health is not reachable on :8090."


def test_request_password_reset_returns_204(start_pb):
    _clear_mailpit()
    resp = _request_password_reset(TEST_USER_EMAIL)
    assert resp.status_code == 204, (
        f"Expected HTTP 204 from request-password-reset, got {resp.status_code}: {resp.text}"
    )


def test_exactly_one_email_with_overridden_content(start_pb):
    _clear_mailpit()
    resp = _request_password_reset(TEST_USER_EMAIL)
    assert resp.status_code == 204, (
        f"request-password-reset did not return 204: {resp.status_code} {resp.text}"
    )

    messages = _wait_for_messages(expected=1, timeout=15.0)
    assert len(messages) == 1, (
        f"Expected exactly 1 email in Mailpit after the reset request, got {len(messages)}."
    )

    summary = messages[0]
    message_id = summary.get("ID") or summary.get("id")
    assert message_id, f"Mailpit message summary missing ID field: {summary!r}"

    # Recipient preserved
    to_list = summary.get("To") or []
    to_addresses = [
        (entry.get("Address") or entry.get("address") or "").lower() for entry in to_list
    ]
    assert TEST_USER_EMAIL.lower() in to_addresses, (
        f"Original recipient {TEST_USER_EMAIL!r} was not preserved; To = {to_list!r}."
    )

    # Subject overridden
    subject = summary.get("Subject") or ""
    assert subject == "Reset your acme.com password", (
        f"Subject was not overridden exactly. Expected 'Reset your acme.com password', got {subject!r}."
    )

    # HTML body
    detail = _get_mailpit_message(message_id)
    html = (detail.get("HTML") or "").strip()
    pattern = (
        r"^Hi "
        + re.escape(TEST_USER_NAME)
        + r"! Use this link: https://acme\.com/reset\?token=("
        + JWT_RE
        + r")$"
    )
    match = re.match(pattern, html)
    assert match is not None, (
        f"HTML body did not match expected override format.\n"
        f"Expected pattern: {pattern}\nGot: {html!r}"
    )

    token = match.group(1)
    payload = _decode_jwt_payload(token)
    assert payload.get("type") == "passwordReset", (
        f"JWT payload type is not 'passwordReset': {payload!r}"
    )
    assert payload.get("collectionId"), (
        f"JWT payload is missing collectionId claim: {payload!r}"
    )
    exp = payload.get("exp")
    assert isinstance(exp, (int, float)) and exp > time.time(), (
        f"JWT exp claim is missing or not in the future: {payload!r}"
    )


def test_empty_name_falls_back_to_email(start_pb):
    token = _superuser_token()
    record_id = _find_user_record_id(token, TEST_USER_EMAIL)

    # Set the name to empty, then trigger another reset.
    _patch_user(token, record_id, {"name": ""})
    try:
        _clear_mailpit()
        resp = _request_password_reset(TEST_USER_EMAIL)
        assert resp.status_code == 204, (
            f"request-password-reset (empty name) did not return 204: "
            f"{resp.status_code} {resp.text}"
        )
        messages = _wait_for_messages(expected=1, timeout=15.0)
        assert len(messages) == 1, (
            f"Expected exactly 1 email after empty-name reset, got {len(messages)}."
        )
        summary = messages[0]
        message_id = summary.get("ID") or summary.get("id")
        detail = _get_mailpit_message(message_id)
        html = (detail.get("HTML") or "").strip()
        pattern = (
            r"^Hi "
            + re.escape(TEST_USER_EMAIL)
            + r"! Use this link: https://acme\.com/reset\?token="
            + JWT_RE
            + r"$"
        )
        assert re.match(pattern, html) is not None, (
            "When name is empty, HTML body must fall back to the user's email.\n"
            f"Expected pattern: {pattern}\nGot: {html!r}"
        )
    finally:
        # Best-effort restore.
        try:
            _patch_user(token, record_id, {"name": TEST_USER_NAME})
        except AssertionError:
            pass
