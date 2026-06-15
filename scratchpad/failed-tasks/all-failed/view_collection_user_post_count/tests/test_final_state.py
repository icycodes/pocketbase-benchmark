import os
import socket
import subprocess
import time
import uuid
from urllib.parse import quote

import pytest
import requests
from xprocess import ProcessStarter

PROJECT_DIR = "/home/user/myproject"
PB_HOST = "127.0.0.1"
PB_PORT = 8090
PB_BASE_URL = f"http://{PB_HOST}:{PB_PORT}"


def _port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        try:
            return s.connect_ex((host, port)) == 0
        except OSError:
            return False


def _kill_existing_pocketbase():
    """Make sure no stale PocketBase server is bound to port 8090 before the
    verifier starts a fresh one."""
    # Best-effort, ignore failures.
    subprocess.run(["pkill", "-f", "pocketbase"], capture_output=True)
    subprocess.run(["pkill", "-f", "/myapp"], capture_output=True)
    subprocess.run(["pkill", "-f", "go-build"], capture_output=True)
    subprocess.run(["pkill", "-f", "go run . serve"], capture_output=True)
    deadline = time.time() + 15
    while _port_open(PB_HOST, PB_PORT) and time.time() < deadline:
        time.sleep(0.5)


@pytest.fixture(scope="session")
def pocketbase_server(xprocess):
    _kill_existing_pocketbase()

    class Starter(ProcessStarter):
        name = "pocketbase_final"
        args = ["go", "run", ".", "serve", f"--http={PB_HOST}:{PB_PORT}"]
        env = os.environ.copy()
        popen_kwargs = {"cwd": PROJECT_DIR, "text": True}
        timeout = 240
        terminate_on_interrupt = True

        def startup_check(self):
            return _port_open(PB_HOST, PB_PORT)

    xprocess.ensure(Starter.name, Starter)

    yield

    info = xprocess.getinfo(Starter.name)
    info.terminate()


@pytest.fixture(scope="session")
def superuser_token(pocketbase_server) -> str:
    email = os.environ["POCKETBASE_SUPERUSER_EMAIL"]
    password = os.environ["POCKETBASE_SUPERUSER_PASSWORD"]
    deadline = time.time() + 60
    last_err = ""
    while time.time() < deadline:
        try:
            resp = requests.post(
                f"{PB_BASE_URL}/api/collections/_superusers/auth-with-password",
                json={"identity": email, "password": password},
                timeout=10,
            )
            if resp.status_code == 200 and resp.json().get("token"):
                return resp.json()["token"]
            last_err = f"status={resp.status_code} body={resp.text!r}"
        except requests.RequestException as exc:
            last_err = str(exc)
        time.sleep(1.0)
    pytest.fail(f"Could not authenticate as superuser: {last_err}")


@pytest.fixture(scope="session")
def seeded_data(pocketbase_server, superuser_token):
    """Create three users (two with posts, one without) and return the captured
    ids / emails / latest-post timestamps for the verification assertions."""
    headers = {"Authorization": superuser_token}
    suffix = uuid.uuid4().hex[:8]

    users_spec = [
        ("alice", f"alice-{suffix}@example.com"),
        ("bob", f"bob-{suffix}@example.com"),
        ("carol", f"carol-{suffix}@example.com"),
    ]
    user_ids = {}
    user_emails = {}
    for label, email in users_spec:
        body = {
            "email": email,
            "password": "Pass1234!",
            "passwordConfirm": "Pass1234!",
        }
        resp = requests.post(
            f"{PB_BASE_URL}/api/collections/users/records",
            json=body,
            headers=headers,
            timeout=30,
        )
        assert resp.status_code in (200, 201), (
            f"Failed to seed user {label} ({email}): status={resp.status_code} "
            f"body={resp.text!r}"
        )
        data = resp.json()
        user_ids[label] = data["id"]
        user_emails[label] = data["email"]

    def _create_post(author_id: str, title: str) -> dict:
        resp = requests.post(
            f"{PB_BASE_URL}/api/collections/posts/records",
            json={"author": author_id, "title": title},
            headers=headers,
            timeout=30,
        )
        assert resp.status_code in (200, 201), (
            f"Failed to create post {title!r}: status={resp.status_code} "
            f"body={resp.text!r}"
        )
        return resp.json()

    alice_latest = None
    for title in ("A1", "A2", "A3"):
        record = _create_post(user_ids["alice"], title)
        alice_latest = record.get("created", "")
        time.sleep(0.05)

    bob_record = _create_post(user_ids["bob"], "B1")
    bob_latest = bob_record.get("created", "")

    return {
        "user_ids": user_ids,
        "user_emails": user_emails,
        "alice_latest": alice_latest or "",
        "bob_latest": bob_latest or "",
    }


def _fetch_all_items(url: str, token: str) -> list:
    """Fetch every page of a records list endpoint and return a flat list."""
    page = 1
    items: list = []
    while True:
        sep = "&" if "?" in url else "?"
        paged_url = f"{url}{sep}page={page}&perPage=200"
        resp = requests.get(
            paged_url, headers={"Authorization": token}, timeout=30
        )
        assert resp.status_code == 200, (
            f"GET {paged_url} expected status 200, got {resp.status_code}: "
            f"{resp.text!r}"
        )
        data = resp.json()
        page_items = data.get("items", [])
        items.extend(page_items)
        total_pages = data.get("totalPages", 1)
        if page >= total_pages or not page_items:
            break
        page += 1
    return items


def test_user_post_stats_sorted_by_post_count_desc(superuser_token, seeded_data):
    items = _fetch_all_items(
        f"{PB_BASE_URL}/api/collections/user_post_stats/records?sort=-post_count",
        superuser_token,
    )
    by_id = {item.get("id"): item for item in items}

    alice_id = seeded_data["user_ids"]["alice"]
    bob_id = seeded_data["user_ids"]["bob"]
    carol_id = seeded_data["user_ids"]["carol"]

    for label, uid in (("alice", alice_id), ("bob", bob_id), ("carol", carol_id)):
        assert uid in by_id, (
            f"View collection `user_post_stats` is missing a row for {label} "
            f"(user id={uid}). Returned ids: {list(by_id.keys())!r}."
        )

    alice_row = by_id[alice_id]
    assert alice_row.get("user") == alice_id, (
        f"alice row `user` field expected {alice_id!r}, got: {alice_row!r}"
    )
    assert alice_row.get("email") == seeded_data["user_emails"]["alice"], (
        f"alice row `email` mismatch: {alice_row!r}"
    )
    assert alice_row.get("post_count") == 3, (
        f"alice row `post_count` expected 3, got: {alice_row!r}"
    )
    alice_last = alice_row.get("last_post_at", "")
    assert isinstance(alice_last, str) and alice_last != "", (
        f"alice row `last_post_at` must be a non-empty string: {alice_row!r}"
    )
    assert alice_last == seeded_data["alice_latest"], (
        "alice row `last_post_at` must equal her latest post `created` "
        f"timestamp {seeded_data['alice_latest']!r}, got: {alice_last!r}"
    )

    bob_row = by_id[bob_id]
    assert bob_row.get("user") == bob_id, f"bob row `user` mismatch: {bob_row!r}"
    assert bob_row.get("email") == seeded_data["user_emails"]["bob"], (
        f"bob row `email` mismatch: {bob_row!r}"
    )
    assert bob_row.get("post_count") == 1, (
        f"bob row `post_count` expected 1, got: {bob_row!r}"
    )
    bob_last = bob_row.get("last_post_at", "")
    assert isinstance(bob_last, str) and bob_last != "", (
        f"bob row `last_post_at` must be a non-empty string: {bob_row!r}"
    )
    assert bob_last == seeded_data["bob_latest"], (
        "bob row `last_post_at` must equal his post `created` timestamp "
        f"{seeded_data['bob_latest']!r}, got: {bob_last!r}"
    )

    carol_row = by_id[carol_id]
    assert carol_row.get("user") == carol_id, (
        f"carol row `user` mismatch: {carol_row!r}"
    )
    assert carol_row.get("email") == seeded_data["user_emails"]["carol"], (
        f"carol row `email` mismatch: {carol_row!r}"
    )
    assert carol_row.get("post_count") == 0, (
        f"carol row `post_count` expected 0, got: {carol_row!r}"
    )
    assert carol_row.get("last_post_at", None) == "", (
        "carol row `last_post_at` must be an empty string when she has no "
        f"posts, got: {carol_row!r}"
    )

    seeded_ids = {alice_id, bob_id, carol_id}
    seeded_order = [item["id"] for item in items if item.get("id") in seeded_ids]
    assert seeded_order == [alice_id, bob_id, carol_id], (
        "With `?sort=-post_count`, the seeded users must appear in descending "
        f"post_count order (alice, bob, carol). Got: {seeded_order!r}"
    )


def test_user_post_stats_filter_post_count_gt_zero(superuser_token, seeded_data):
    filter_expr = quote("(post_count>0)")
    items = _fetch_all_items(
        f"{PB_BASE_URL}/api/collections/user_post_stats/records?filter={filter_expr}",
        superuser_token,
    )
    returned_ids = {item.get("id") for item in items}

    alice_id = seeded_data["user_ids"]["alice"]
    bob_id = seeded_data["user_ids"]["bob"]
    carol_id = seeded_data["user_ids"]["carol"]

    assert alice_id in returned_ids, (
        f"Filter `(post_count>0)` must include alice (id={alice_id}). "
        f"Returned ids: {returned_ids!r}"
    )
    assert bob_id in returned_ids, (
        f"Filter `(post_count>0)` must include bob (id={bob_id}). "
        f"Returned ids: {returned_ids!r}"
    )
    assert carol_id not in returned_ids, (
        f"Filter `(post_count>0)` must NOT include carol (id={carol_id}). "
        f"Returned ids: {returned_ids!r}"
    )

    for item in items:
        post_count = item.get("post_count")
        assert isinstance(post_count, int) and post_count > 0, (
            "Every item returned by the filter must have integer "
            f"post_count>0. Offending row: {item!r}"
        )
