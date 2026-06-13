import os
import socket
import subprocess
import time

import pytest
import requests
from xprocess import ProcessStarter


PROJECT_DIR = "/home/user/myproject"
BASE_URL = "http://localhost:8090"
COLLECTION_URL = f"{BASE_URL}/api/collections/articles/records"


def _wait_for_port(host: str, port: int, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1.0)
            if s.connect_ex((host, port)) == 0:
                return True
        time.sleep(0.5)
    return False


def _wait_for_health(timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"{BASE_URL}/api/health", timeout=2)
            if r.status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(0.5)
    return False


@pytest.fixture(scope="session", autouse=True)
def _reset_database():
    """Remove any leftover SQLite state so the migration re-runs from a clean slate."""
    pb_data = os.path.join(PROJECT_DIR, "pb_data")
    for name in ("data.db", "data.db-shm", "data.db-wal"):
        p = os.path.join(pb_data, name)
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass
    yield


@pytest.fixture(scope="session")
def pocketbase_server(xprocess, _reset_database):
    """Build the project and start the PocketBase server in the background."""
    build = subprocess.run(
        ["go", "build", "-o", "articles-app", "."],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        timeout=240,
    )
    assert build.returncode == 0, (
        f"`go build` failed in {PROJECT_DIR}: stderr=\n{build.stderr}\nstdout=\n{build.stdout}"
    )

    class Starter(ProcessStarter):
        name = "pocketbase_server"
        args = [os.path.join(PROJECT_DIR, "articles-app"), "serve", "--http=0.0.0.0:8090"]
        env = os.environ.copy()
        popen_kwargs = {
            "cwd": PROJECT_DIR,
            "text": True,
        }
        timeout = 60
        terminate_on_interrupt = True

        def startup_check(self):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1.0)
                return s.connect_ex(("localhost", 8090)) == 0

    xprocess.ensure(Starter.name, Starter)

    assert _wait_for_port("localhost", 8090, timeout=30), (
        "PocketBase did not start listening on port 8090."
    )
    assert _wait_for_health(timeout=30), (
        "PocketBase /api/health endpoint did not return 200 after start."
    )

    yield

    info = xprocess.getinfo(Starter.name)
    info.terminate()


def _post_article(body: dict) -> requests.Response:
    return requests.post(COLLECTION_URL, json=body, timeout=10)


def test_simple_slug_generation(pocketbase_server):
    r = _post_article({"title": "Hello World", "content": "first post"})
    assert r.status_code == 200, (
        f"Expected HTTP 200 when creating an article with a simple title, got {r.status_code}: {r.text}"
    )
    data = r.json()
    assert data.get("title") == "Hello World", (
        f"Expected title 'Hello World' in response, got: {data}"
    )
    assert data.get("slug") == "hello-world", (
        f"Expected slug 'hello-world' to be auto-generated, got: {data.get('slug')!r}"
    )


def test_punctuation_and_casing_collapse(pocketbase_server):
    r = _post_article({"title": "My First Post!"})
    assert r.status_code == 200, (
        f"Expected HTTP 200 for 'My First Post!', got {r.status_code}: {r.text}"
    )
    data = r.json()
    assert data.get("slug") == "my-first-post", (
        f"Expected slug 'my-first-post' for title 'My First Post!', got: {data.get('slug')!r}"
    )


def test_mixed_symbols_and_numbers(pocketbase_server):
    r = _post_article({"title": "  Tech & Science 2026!!  "})
    assert r.status_code == 200, (
        f"Expected HTTP 200 for 'Tech & Science 2026!!', got {r.status_code}: {r.text}"
    )
    data = r.json()
    assert data.get("slug") == "tech-science-2026", (
        "Expected slug 'tech-science-2026' (collapsed runs of non-alphanumeric characters, "
        f"no leading/trailing dashes), got: {data.get('slug')!r}"
    )


def test_client_supplied_slug_is_overwritten(pocketbase_server):
    r = _post_article({"title": "Override Me", "slug": "client-chosen-slug"})
    assert r.status_code == 200, (
        f"Expected HTTP 200 when client supplies a slug, got {r.status_code}: {r.text}"
    )
    data = r.json()
    assert data.get("slug") == "override-me", (
        "The server-side hook must overwrite any client-supplied slug with one derived from the title; "
        f"got: {data.get('slug')!r}"
    )


def test_empty_title_is_rejected(pocketbase_server):
    r = _post_article({"title": "", "content": "nope"})
    assert r.status_code == 400, (
        f"Expected HTTP 400 for empty title, got {r.status_code}: {r.text}"
    )

    list_r = requests.get(
        COLLECTION_URL,
        params={"filter": '(content="nope")'},
        timeout=10,
    )
    assert list_r.status_code == 200, (
        f"Could not list articles to confirm rejection persisted nothing: {list_r.text}"
    )
    assert list_r.json().get("totalItems", -1) == 0, (
        f"Expected no article persisted when title is empty, but list returned: {list_r.text}"
    )


def test_whitespace_only_title_is_rejected(pocketbase_server):
    r = _post_article({"title": "   ", "content": "whitespace-only"})
    assert r.status_code == 400, (
        f"Expected HTTP 400 for whitespace-only title, got {r.status_code}: {r.text}"
    )

    list_r = requests.get(
        COLLECTION_URL,
        params={"filter": '(content="whitespace-only")'},
        timeout=10,
    )
    assert list_r.status_code == 200, (
        f"Could not list articles to confirm rejection persisted nothing: {list_r.text}"
    )
    assert list_r.json().get("totalItems", -1) == 0, (
        f"Expected no article persisted when title is whitespace-only, but list returned: {list_r.text}"
    )


def test_chain_is_not_blocked(pocketbase_server):
    r = requests.get(COLLECTION_URL, params={"sort": "created", "perPage": 200}, timeout=10)
    assert r.status_code == 200, f"Could not list articles after creates: {r.text}"
    payload = r.json()
    items = payload.get("items", [])
    titles = [item.get("title") for item in items]
    expected_titles = {
        "Hello World",
        "My First Post!",
        "  Tech & Science 2026!!  ",
        "Override Me",
    }
    missing = expected_titles - set(titles)
    assert not missing, (
        "The hook appears to be blocking record persistence (forgot to call e.Next()?). "
        f"Missing expected titles in the articles collection: {missing}. Found: {titles}"
    )
