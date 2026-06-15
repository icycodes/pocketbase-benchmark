import os
import socket
import subprocess
import time

import pytest
import requests
from xprocess import ProcessStarter

PROJECT_DIR = "/home/user/myproject"
BINARY_PATH = os.path.join(PROJECT_DIR, "app")
BASE_URL = "http://127.0.0.1:8090"
SUPERUSER_EMAIL = "admin@example.com"
SUPERUSER_PASSWORD = "SuperSecret123"


def _port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def _wait_for_health(timeout: float = 60.0) -> None:
    deadline = time.time() + timeout
    last_err = None
    while time.time() < deadline:
        try:
            r = requests.get(f"{BASE_URL}/api/health", timeout=2)
            if r.status_code == 200:
                return
        except Exception as exc:
            last_err = exc
        time.sleep(0.5)
    raise RuntimeError(f"PocketBase /api/health did not become ready in time: {last_err}")


@pytest.fixture(scope="session", autouse=True)
def start_pocketbase(xprocess):
    """Build the binary if needed, ensure the superuser exists, and run `serve`."""

    # Build the binary if it is missing (the executor is expected to build it,
    # but make verification robust if they only edited source files).
    if not os.path.isfile(BINARY_PATH):
        build = subprocess.run(
            ["go", "build", "-o", "app", "."],
            capture_output=True,
            text=True,
            cwd=PROJECT_DIR,
        )
        assert build.returncode == 0, (
            f"Failed to build PocketBase application: {build.stderr}"
        )

    # Ensure the superuser exists; "upsert" is idempotent.
    upsert = subprocess.run(
        [BINARY_PATH, "superuser", "upsert", SUPERUSER_EMAIL, SUPERUSER_PASSWORD],
        capture_output=True,
        text=True,
        cwd=PROJECT_DIR,
    )
    assert upsert.returncode == 0, (
        f"Failed to upsert PocketBase superuser: {upsert.stderr}"
    )

    class Starter(ProcessStarter):
        name = "pocketbase_serve"
        args = [BINARY_PATH, "serve", "--http=0.0.0.0:8090"]
        env = os.environ.copy()
        popen_kwargs = {
            "cwd": PROJECT_DIR,
            "text": True,
        }
        timeout = 120
        terminate_on_interrupt = True

        def startup_check(self):
            return _port_open("127.0.0.1", 8090)

    xprocess.ensure(Starter.name, Starter)
    _wait_for_health()

    yield

    info = xprocess.getinfo(Starter.name)
    info.terminate()


@pytest.fixture(scope="session")
def auth_token(start_pocketbase) -> str:
    resp = requests.post(
        f"{BASE_URL}/api/collections/_superusers/auth-with-password",
        json={"identity": SUPERUSER_EMAIL, "password": SUPERUSER_PASSWORD},
        timeout=10,
    )
    assert resp.status_code == 200, (
        f"Superuser auth failed (status {resp.status_code}): {resp.text}"
    )
    body = resp.json()
    token = body.get("token")
    assert isinstance(token, str) and token, (
        f"Auth response did not contain a token: {body}"
    )
    return token


def _auth_headers(token: str) -> dict:
    return {"Authorization": token, "Content-Type": "application/json"}


def _create_article(token: str, payload: dict) -> requests.Response:
    return requests.post(
        f"{BASE_URL}/api/collections/articles/records",
        headers=_auth_headers(token),
        json=payload,
        timeout=10,
    )


def _update_article(token: str, record_id: str, payload: dict) -> requests.Response:
    return requests.patch(
        f"{BASE_URL}/api/collections/articles/records/{record_id}",
        headers=_auth_headers(token),
        json=payload,
        timeout=10,
    )


def test_short_article_word_count(auth_token: str):
    """4 whitespace-separated words -> word_count = 4, reading_time_minutes = 1."""
    resp = _create_article(
        auth_token,
        {"title": "Short post", "content": "alpha beta gamma delta"},
    )
    assert resp.status_code == 200 or resp.status_code == 201, (
        f"Expected 200/201 on create, got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    assert body.get("word_count") == 4, (
        f"Expected word_count == 4 for 'alpha beta gamma delta', got {body.get('word_count')} (full body: {body})."
    )
    assert body.get("reading_time_minutes") == 1, (
        f"Expected reading_time_minutes == 1 for word_count 4, got {body.get('reading_time_minutes')} (full body: {body})."
    )


def test_long_article_word_count(auth_token: str):
    """250 whitespace-separated tokens -> word_count = 250, reading_time_minutes = 2."""
    tokens = [f"w{i}" for i in range(1, 251)]
    content = " ".join(tokens)
    resp = _create_article(
        auth_token,
        {"title": "Long post", "content": content},
    )
    assert resp.status_code in (200, 201), (
        f"Expected 200/201 on create, got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    assert body.get("word_count") == 250, (
        f"Expected word_count == 250, got {body.get('word_count')} (full body: {body})."
    )
    assert body.get("reading_time_minutes") == 2, (
        f"Expected reading_time_minutes == 2 for 250 words, got {body.get('reading_time_minutes')}."
    )


def test_hook_overrides_client_supplied_counters(auth_token: str):
    """Client-supplied word_count/reading_time_minutes must be overwritten."""
    resp = _create_article(
        auth_token,
        {
            "title": "Lying post",
            "content": "one two three",
            "word_count": 999,
            "reading_time_minutes": 999,
        },
    )
    assert resp.status_code in (200, 201), (
        f"Expected 200/201 on create, got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    assert body.get("word_count") == 3, (
        f"Expected word_count == 3 ('one two three'), but got {body.get('word_count')}. "
        "The hook must overwrite client-supplied word_count values."
    )
    assert body.get("reading_time_minutes") == 1, (
        f"Expected reading_time_minutes == 1 for 3 words, got {body.get('reading_time_minutes')}. "
        "The hook must overwrite client-supplied reading_time_minutes values."
    )


def test_update_recomputes_counters(auth_token: str):
    """Updating an article must recompute word_count and reading_time_minutes."""
    create = _create_article(
        auth_token,
        {"title": "To update", "content": "alpha beta gamma delta"},
    )
    assert create.status_code in (200, 201), (
        f"Setup create failed (status {create.status_code}): {create.text}"
    )
    record_id = create.json().get("id")
    assert isinstance(record_id, str) and record_id, (
        f"Created article must return an id; got: {create.json()}"
    )

    update = _update_article(auth_token, record_id, {"content": "hello world"})
    assert update.status_code == 200, (
        f"Expected 200 on update, got {update.status_code}: {update.text}"
    )
    body = update.json()
    assert body.get("word_count") == 2, (
        f"Expected word_count == 2 after update to 'hello world', got {body.get('word_count')}."
    )
    assert body.get("reading_time_minutes") == 1, (
        f"Expected reading_time_minutes == 1 for 2 words, got {body.get('reading_time_minutes')}."
    )


def test_empty_content_yields_zero(auth_token: str):
    """Whitespace-only content yields word_count = 0 and reading_time_minutes = 0."""
    resp = _create_article(
        auth_token,
        {"title": "Empty", "content": "   "},
    )
    assert resp.status_code in (200, 201), (
        f"Expected 200/201 on create, got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    assert body.get("word_count") == 0, (
        f"Expected word_count == 0 for whitespace-only content, got {body.get('word_count')}."
    )
    assert body.get("reading_time_minutes") == 0, (
        f"Expected reading_time_minutes == 0 for 0 words, got {body.get('reading_time_minutes')}."
    )
