import json
import os
import queue
import re
import socket
import subprocess
import threading
import time
from typing import Optional

import pytest
import requests
from xprocess import ProcessStarter

PROJECT_DIR = "/home/user/myproject"
PB_BIN = os.path.join(PROJECT_DIR, "pocketbase")
PB_URL = "http://127.0.0.1:8090"

SUPERUSER_EMAIL = "admin@example.com"
SUPERUSER_PASSWORD = "SuperAdmin1234"

ALICE_EMAIL = "alice@example.com"
ALICE_PASSWORD = "AlicePass1234"

BOB_EMAIL = "bob@example.com"
BOB_PASSWORD = "BobPass1234"

EXPECTED_RULE = "recipient = @request.auth.id"

# Maximum time to wait for SSE events after creating records.
SSE_WAIT_SECONDS = 5.0


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def pb_server(xprocess):
    """Start the PocketBase server for the duration of the verification run."""

    class Starter(ProcessStarter):
        name = "pb_server_final"
        args = [PB_BIN, "serve", "--http=0.0.0.0:8090"]
        env = os.environ.copy()
        popen_kwargs = {
            "cwd": PROJECT_DIR,
            "text": True,
        }
        timeout = 60
        terminate_on_interrupt = True

        def startup_check(self):
            try:
                r = requests.get(f"{PB_URL}/api/health", timeout=2)
                return r.status_code == 200
            except Exception:
                return False

    # If a previous run left a server bound to 8090, reuse it; otherwise
    # spawn a new one via xprocess.
    if not _port_open("127.0.0.1", 8090):
        xprocess.ensure(Starter.name, Starter)

    # Sanity-poll until healthy regardless of which branch we took.
    _wait_for_health(timeout=30.0)
    yield

    try:
        info = xprocess.getinfo(Starter.name)
        info.terminate()
    except Exception:
        pass


def _port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        return s.connect_ex((host, port)) == 0


def _wait_for_health(timeout: float):
    deadline = time.time() + timeout
    last_err: Optional[Exception] = None
    while time.time() < deadline:
        try:
            r = requests.get(f"{PB_URL}/api/health", timeout=2)
            if r.status_code == 200:
                return
        except Exception as e:  # pragma: no cover - defensive
            last_err = e
        time.sleep(0.5)
    raise RuntimeError(f"PocketBase did not become healthy: last_err={last_err!r}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _auth_superuser() -> str:
    r = requests.post(
        f"{PB_URL}/api/collections/_superusers/auth-with-password",
        json={"identity": SUPERUSER_EMAIL, "password": SUPERUSER_PASSWORD},
        timeout=10,
    )
    assert r.status_code == 200, f"Superuser auth failed: {r.status_code} {r.text!r}"
    token = r.json().get("token")
    assert token, f"Superuser auth response missing token: {r.text!r}"
    return token


def _auth_user(email: str, password: str):
    r = requests.post(
        f"{PB_URL}/api/collections/users/auth-with-password",
        json={"identity": email, "password": password},
        timeout=10,
    )
    assert r.status_code == 200, (
        f"User auth for {email} failed: {r.status_code} {r.text!r}"
    )
    body = r.json()
    token = body.get("token")
    record = body.get("record") or {}
    user_id = record.get("id")
    assert token and user_id, (
        f"User auth response for {email} missing token or record id: {body!r}"
    )
    return token, user_id


def _normalize_rule(rule: Optional[str]) -> str:
    if rule is None:
        return ""
    # Collapse whitespace and strip for stable comparison.
    return re.sub(r"\s+", " ", rule.strip())


class SSESubscriber:
    """Minimal Server-Sent Events client for PocketBase realtime.

    The client opens a long-lived GET /api/realtime stream, captures the
    PB_CONNECT clientId, calls POST /api/realtime to register a subscription,
    and then exposes the subsequent events to the caller through a queue.
    """

    def __init__(self, token: Optional[str] = None):
        self._token = token
        self._session = requests.Session()
        self._stream: Optional[requests.Response] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._connect_evt = threading.Event()
        self._client_id: Optional[str] = None
        self._events: "queue.Queue[dict]" = queue.Queue()

    def _headers(self) -> dict:
        h = {"Accept": "text/event-stream"}
        if self._token:
            h["Authorization"] = self._token
        return h

    def _reader_loop(self):
        assert self._stream is not None
        try:
            event_name: Optional[str] = None
            data_buf: list[str] = []
            for raw in self._stream.iter_lines(decode_unicode=True):
                if self._stop.is_set():
                    break
                if raw is None:
                    continue
                line = raw.rstrip("\r")
                if line == "":
                    # End of one SSE message.
                    if event_name is not None or data_buf:
                        body = "\n".join(data_buf)
                        parsed: dict = {"event": event_name, "raw": body}
                        try:
                            parsed["json"] = json.loads(body) if body else None
                        except Exception:
                            parsed["json"] = None
                        if event_name == "PB_CONNECT":
                            cid = (parsed.get("json") or {}).get("clientId")
                            if cid:
                                self._client_id = cid
                                self._connect_evt.set()
                        else:
                            self._events.put(parsed)
                    event_name = None
                    data_buf = []
                    continue
                if line.startswith(":"):
                    # SSE comment / heartbeat — ignore.
                    continue
                if line.startswith("event:"):
                    event_name = line[len("event:"):].strip()
                elif line.startswith("data:"):
                    data_buf.append(line[len("data:"):].lstrip())
                # id: and retry: are ignored.
        except Exception:
            # Stream closed or network error; just exit.
            return

    def start(self):
        self._stream = self._session.get(
            f"{PB_URL}/api/realtime",
            headers=self._headers(),
            stream=True,
            timeout=(10, None),
        )
        assert self._stream.status_code == 200, (
            f"GET /api/realtime failed: {self._stream.status_code} {self._stream.text!r}"
        )
        self._reader_thread = threading.Thread(
            target=self._reader_loop, daemon=True
        )
        self._reader_thread.start()
        ok = self._connect_evt.wait(timeout=10.0)
        assert ok and self._client_id, (
            "Did not receive PB_CONNECT clientId from /api/realtime within 10s."
        )

    def subscribe(self, topics: list[str]) -> int:
        assert self._client_id is not None
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = self._token
        r = requests.post(
            f"{PB_URL}/api/realtime",
            headers=headers,
            json={"clientId": self._client_id, "subscriptions": topics},
            timeout=10,
        )
        return r.status_code

    def collect_create_events(
        self, collection: str, duration: float
    ) -> list[dict]:
        """Drain events for `duration` seconds and return notification create events."""
        deadline = time.time() + duration
        out: list[dict] = []
        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                break
            try:
                evt = self._events.get(timeout=remaining)
            except queue.Empty:
                break
            # Event names look like "<collectionId-or-name>/<recordId>" OR
            # the raw topic the client subscribed to. We match either the
            # collection name prefix or detect via the payload.
            ev_name = (evt.get("event") or "")
            payload = evt.get("json") or {}
            action = payload.get("action")
            record = payload.get("record") or {}
            collection_name = record.get("collectionName")
            if action == "create" and (
                collection_name == collection or ev_name.startswith(f"{collection}/")
            ):
                out.append(evt)
        return out

    def close(self):
        self._stop.set()
        try:
            if self._stream is not None:
                self._stream.close()
        except Exception:
            pass


def _create_notification(admin_token: str, recipient_id: str, message: str) -> str:
    r = requests.post(
        f"{PB_URL}/api/collections/notifications/records",
        headers={"Authorization": admin_token, "Content-Type": "application/json"},
        json={"recipient": recipient_id, "message": message},
        timeout=10,
    )
    assert r.status_code in (200, 201), (
        f"Failed to create notification record: status={r.status_code} body={r.text!r}"
    )
    body = r.json()
    return body.get("id")


def _delete_all_notifications(admin_token: str):
    try:
        r = requests.get(
            f"{PB_URL}/api/collections/notifications/records",
            headers={"Authorization": admin_token},
            params={"perPage": 200},
            timeout=10,
        )
        if r.status_code != 200:
            return
        items = (r.json() or {}).get("items") or []
        for item in items:
            rid = item.get("id")
            if not rid:
                continue
            requests.delete(
                f"{PB_URL}/api/collections/notifications/records/{rid}",
                headers={"Authorization": admin_token},
                timeout=10,
            )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_notifications_collection_shape_and_rules(pb_server):
    admin_token = _auth_superuser()

    # Get the users collection id for relation field validation.
    r_users = requests.get(
        f"{PB_URL}/api/collections/users",
        headers={"Authorization": admin_token},
        timeout=10,
    )
    assert r_users.status_code == 200, (
        f"Failed to fetch users collection metadata: {r_users.status_code} {r_users.text!r}"
    )
    users_collection_id = r_users.json().get("id")
    assert users_collection_id, (
        f"users collection metadata missing id: {r_users.text!r}"
    )

    r = requests.get(
        f"{PB_URL}/api/collections/notifications",
        headers={"Authorization": admin_token},
        timeout=10,
    )
    assert r.status_code == 200, (
        f"Expected the `notifications` collection to exist and be readable by "
        f"a superuser: status={r.status_code} body={r.text!r}"
    )
    coll = r.json()

    assert coll.get("type") == "base", (
        f"`notifications` collection must be of type 'base', got: {coll.get('type')!r}"
    )

    assert _normalize_rule(coll.get("listRule")) == EXPECTED_RULE, (
        f"`notifications.listRule` must be {EXPECTED_RULE!r}, got: "
        f"{coll.get('listRule')!r}"
    )
    assert _normalize_rule(coll.get("viewRule")) == EXPECTED_RULE, (
        f"`notifications.viewRule` must be {EXPECTED_RULE!r}, got: "
        f"{coll.get('viewRule')!r}"
    )

    fields = coll.get("fields") or coll.get("schema") or []
    field_by_name = {f.get("name"): f for f in fields}

    recipient = field_by_name.get("recipient")
    assert recipient is not None, (
        f"`notifications` collection is missing the `recipient` field. "
        f"Fields present: {list(field_by_name.keys())}"
    )
    assert recipient.get("type") == "relation", (
        f"`recipient` field must be of type 'relation', got: {recipient.get('type')!r}"
    )
    assert recipient.get("required") is True, (
        f"`recipient` field must be required, got: {recipient.get('required')!r}"
    )
    assert recipient.get("maxSelect") == 1, (
        f"`recipient` field must have maxSelect == 1, got: {recipient.get('maxSelect')!r}"
    )
    assert recipient.get("collectionId") == users_collection_id, (
        f"`recipient` field must target the users collection "
        f"(id={users_collection_id!r}); got collectionId={recipient.get('collectionId')!r}"
    )

    message = field_by_name.get("message")
    assert message is not None, (
        f"`notifications` collection is missing the `message` field. "
        f"Fields present: {list(field_by_name.keys())}"
    )
    assert message.get("type") == "text", (
        f"`message` field must be of type 'text', got: {message.get('type')!r}"
    )


def test_realtime_alice_receives_only_her_own_events(pb_server):
    admin_token = _auth_superuser()
    alice_token, alice_id = _auth_user(ALICE_EMAIL, ALICE_PASSWORD)
    _, bob_id = _auth_user(BOB_EMAIL, BOB_PASSWORD)

    _delete_all_notifications(admin_token)

    sub = SSESubscriber(token=alice_token)
    try:
        sub.start()
        status = sub.subscribe(["notifications"])
        assert status in (200, 204), (
            f"POST /api/realtime for Alice failed: status={status}"
        )

        # Give PocketBase a brief moment to register the subscription.
        time.sleep(0.5)

        _create_notification(admin_token, alice_id, "hello alice 1")
        _create_notification(admin_token, bob_id, "hello bob 1")
        _create_notification(admin_token, alice_id, "hello alice 2")

        events = sub.collect_create_events("notifications", SSE_WAIT_SECONDS)
    finally:
        sub.close()
        _delete_all_notifications(admin_token)

    assert len(events) == 2, (
        f"Alice expected exactly 2 `create` events on the `notifications` "
        f"topic, got {len(events)}: {[e.get('json') for e in events]}"
    )
    for evt in events:
        record = (evt.get("json") or {}).get("record") or {}
        assert record.get("recipient") == alice_id, (
            f"Alice received a `notifications` event whose recipient is not "
            f"her id (expected {alice_id!r}): {record!r}"
        )


def test_realtime_bob_receives_only_his_own_event(pb_server):
    admin_token = _auth_superuser()
    _, alice_id = _auth_user(ALICE_EMAIL, ALICE_PASSWORD)
    bob_token, bob_id = _auth_user(BOB_EMAIL, BOB_PASSWORD)

    _delete_all_notifications(admin_token)

    sub = SSESubscriber(token=bob_token)
    try:
        sub.start()
        status = sub.subscribe(["notifications"])
        assert status in (200, 204), (
            f"POST /api/realtime for Bob failed: status={status}"
        )

        time.sleep(0.5)

        _create_notification(admin_token, alice_id, "hello alice 1")
        _create_notification(admin_token, bob_id, "hello bob 1")
        _create_notification(admin_token, alice_id, "hello alice 2")

        events = sub.collect_create_events("notifications", SSE_WAIT_SECONDS)
    finally:
        sub.close()
        _delete_all_notifications(admin_token)

    assert len(events) == 1, (
        f"Bob expected exactly 1 `create` event on the `notifications` "
        f"topic, got {len(events)}: {[e.get('json') for e in events]}"
    )
    record = (events[0].get("json") or {}).get("record") or {}
    assert record.get("recipient") == bob_id, (
        f"Bob received a `notifications` event whose recipient is not his id "
        f"(expected {bob_id!r}): {record!r}"
    )


def test_realtime_anonymous_subscriber_receives_no_events(pb_server):
    admin_token = _auth_superuser()
    _, alice_id = _auth_user(ALICE_EMAIL, ALICE_PASSWORD)
    _, bob_id = _auth_user(BOB_EMAIL, BOB_PASSWORD)

    _delete_all_notifications(admin_token)

    sub = SSESubscriber(token=None)
    try:
        sub.start()
        # An anonymous POST /api/realtime is allowed; the server simply binds
        # no auth to the channel, which is exactly what we want to test.
        status = sub.subscribe(["notifications"])
        assert status in (200, 204), (
            f"Anonymous POST /api/realtime failed: status={status}"
        )

        time.sleep(0.5)

        _create_notification(admin_token, alice_id, "hello alice 1")
        _create_notification(admin_token, bob_id, "hello bob 1")
        _create_notification(admin_token, alice_id, "hello alice 2")

        events = sub.collect_create_events("notifications", SSE_WAIT_SECONDS)
    finally:
        sub.close()
        _delete_all_notifications(admin_token)

    assert len(events) == 0, (
        f"Anonymous subscriber must receive zero `notifications` events but "
        f"got {len(events)}: {[e.get('json') for e in events]}"
    )
