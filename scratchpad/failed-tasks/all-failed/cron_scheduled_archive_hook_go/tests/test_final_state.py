import os
import re
import socket
import subprocess
import time
from datetime import datetime, timezone

import pytest
import requests
from xprocess import ProcessStarter

PROJECT_DIR = "/home/user/myproject"
BASE_URL = "http://127.0.0.1:8090"
HEALTH_URL = f"{BASE_URL}/api/health"
POSTS_URL = f"{BASE_URL}/api/collections/posts/records"
ARCHIVE_URL = f"{BASE_URL}/api/collections/archive_posts/records"

ARCHIVE_AGE_SECONDS = "5"


def _run_id() -> str:
    rid = os.environ.get("ZEALT_RUN_ID")
    assert rid, "ZEALT_RUN_ID environment variable is required for run isolation."
    assert re.fullmatch(r"zr-[a-z0-9]+", rid), (
        f"ZEALT_RUN_ID must match `zr-[a-z0-9]+`, got: {rid!r}"
    )
    return rid


def _port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def _health_ok() -> bool:
    try:
        r = requests.get(HEALTH_URL, timeout=2)
        return r.status_code == 200
    except requests.RequestException:
        return False


@pytest.fixture(scope="session", autouse=True)
def build_binary():
    """Ensure the executor's Go binary is compiled before we attempt to start it."""
    result = subprocess.run(
        ["go", "build", "-o", "myapp", "."],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert result.returncode == 0, (
        "Failed to build the Go binary in "
        f"{PROJECT_DIR}:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    binary_path = os.path.join(PROJECT_DIR, "myapp")
    assert os.path.isfile(binary_path), (
        f"`go build` succeeded but the expected binary at {binary_path} is missing."
    )
    yield


@pytest.fixture(scope="session")
def start_server(xprocess, build_binary):
    """Start the embedded PocketBase server with ARCHIVE_AGE_SECONDS=5."""

    class Starter(ProcessStarter):
        name = "pb_archive_app"
        args = ["./myapp", "serve", "--http=0.0.0.0:8090"]
        env = os.environ.copy()
        env["ARCHIVE_AGE_SECONDS"] = ARCHIVE_AGE_SECONDS
        popen_kwargs = {"cwd": PROJECT_DIR, "text": True}
        timeout = 120
        terminate_on_interrupt = True

        def startup_check(self):
            return _port_open("127.0.0.1", 8090) and _health_ok()

    xprocess.ensure(Starter.name, Starter)
    yield
    xprocess.getinfo(Starter.name).terminate()


def _list_records(url: str, run_id: str):
    r = requests.get(
        url,
        params={"perPage": 200, "filter": f'title~"{run_id}-"'},
        timeout=10,
    )
    assert r.status_code == 200, (
        f"GET {url} returned {r.status_code}: {r.text}"
    )
    body = r.json()
    assert "items" in body, f"GET {url} response missing `items`: {body}"
    return body["items"]


def _parse_pb_datetime(value: str) -> datetime:
    """
    PocketBase datetime fields are returned either as ISO-8601
    (e.g. `2025-01-02T03:04:05.123Z`) or PocketBase's own
    `2025-01-02 03:04:05.123Z` form. Accept both.
    """
    assert isinstance(value, str) and value, (
        f"Expected a non-empty datetime string, got: {value!r}"
    )
    normalized = value.replace(" ", "T")
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    return datetime.fromisoformat(normalized).astimezone(timezone.utc)


def _create_post(title: str, content: str) -> dict:
    r = requests.post(
        POSTS_URL,
        json={"title": title, "content": content},
        timeout=10,
    )
    assert r.status_code in (200, 201), (
        f"POST {POSTS_URL} for title={title!r} returned {r.status_code}: {r.text}"
    )
    rec = r.json()
    for key in ("id", "created", "title", "content"):
        assert key in rec, f"Created record missing `{key}`: {rec}"
    return rec


# --------------------------------------------------------------------------- #
# Verification steps                                                          #
# --------------------------------------------------------------------------- #


def test_collections_are_publicly_listable(start_server):
    """Verification step 1: both collections respond 200 to unauthenticated GET."""
    rid = _run_id()
    for url, name in [(POSTS_URL, "posts"), (ARCHIVE_URL, "archive_posts")]:
        r = requests.get(url, params={"perPage": 1, "filter": f'title~"{rid}-"'},
                         timeout=10)
        assert r.status_code == 200, (
            f"Expected {name} collection to be listable without auth "
            f"(GET {url}), got status {r.status_code}: {r.text}"
        )
        body = r.json()
        assert "items" in body, (
            f"Expected `items` key on GET {url} response, got: {body}"
        )


def test_archive_workflow_end_to_end(start_server):
    """Verification steps 2–5: seed posts, wait, check archive/cleanup/atomicity."""
    rid = _run_id()

    # Align the seed to ~7s past a minute boundary so that exactly one cron tick
    # at the next minute boundary fires while the seeded posts are >>5s old, and
    # so that after seeding the fresh post we have ~50s of clearance before the
    # following tick.
    now = time.time()
    align_offset = (7 - (int(now) % 60)) % 60
    if align_offset > 0:
        time.sleep(align_offset)

    # ---- Step 2: seed two "old" posts. ----------------------------------- #
    old1 = _create_post(f"{rid}-old-1", "alpha")
    old2 = _create_post(f"{rid}-old-2", "beta")
    seed_old_at = time.time()
    old_created = {
        old1["id"]: _parse_pb_datetime(old1["created"]),
        old2["id"]: _parse_pb_datetime(old2["created"]),
    }

    # Wait 60 s so the next minute-boundary cron tick fires while these posts
    # are >> ARCHIVE_AGE_SECONDS=5 seconds old.
    time.sleep(60)

    # ---- Now seed the "fresh" post and let any in-flight tick settle. ---- #
    fresh = _create_post(f"{rid}-fresh", "gamma")
    fresh_id = fresh["id"]
    time.sleep(5)
    # Sanity check: we must NOT have crossed into a second cron tick window
    # for the fresh record (would invalidate the "young records stay" check).
    assert time.time() - seed_old_at < 110, (
        "Verification timing drift: spent too long between seeding and "
        "assertion; the fresh post may have aged past the threshold."
    )

    # ---- Step 3: archive_posts must contain exactly the two old records. - #
    archived = _list_records(ARCHIVE_URL, rid)
    archived_by_id = {item["id"]: item for item in archived}

    for old in (old1, old2):
        oid = old["id"]
        assert oid in archived_by_id, (
            f"Expected archived copy of original post id={oid} "
            f"(title={old['title']!r}) in archive_posts; got ids: "
            f"{list(archived_by_id)}"
        )
        copy = archived_by_id[oid]
        assert copy["title"] == old["title"], (
            f"Archived title {copy['title']!r} does not match original "
            f"{old['title']!r} for id={oid}."
        )
        assert copy["content"] == old["content"], (
            f"Archived content {copy['content']!r} does not match original "
            f"{old['content']!r} for id={oid}."
        )
        archived_at_raw = copy.get("archived_at")
        assert archived_at_raw, (
            f"Archived record {oid} missing `archived_at`; got record: {copy}"
        )
        archived_at = _parse_pb_datetime(archived_at_raw)
        original_created = old_created[oid]
        delta = (archived_at - original_created).total_seconds()
        assert 0 <= delta <= 65, (
            f"archived_at for {oid} is {delta:.2f}s after creation "
            f"({archived_at_raw} vs {old['created']}); expected within 65s."
        )

    assert fresh_id not in archived_by_id, (
        f"Fresh post id={fresh_id} (younger than {ARCHIVE_AGE_SECONDS}s at the "
        "last tick) must NOT have been archived."
    )

    # ---- Step 4: posts collection must be cleaned up. -------------------- #
    remaining = _list_records(POSTS_URL, rid)
    remaining_ids = {item["id"] for item in remaining}
    assert old1["id"] not in remaining_ids, (
        f"Original post id={old1['id']} should have been deleted from posts."
    )
    assert old2["id"] not in remaining_ids, (
        f"Original post id={old2['id']} should have been deleted from posts."
    )
    assert fresh_id in remaining_ids, (
        f"Fresh post id={fresh_id} should still be present in posts; "
        f"remaining ids for run {rid}: {remaining_ids}"
    )
    fresh_remaining = next(item for item in remaining if item["id"] == fresh_id)
    assert fresh_remaining["title"] == f"{rid}-fresh", (
        f"Fresh post title got mutated: {fresh_remaining['title']!r}"
    )

    # ---- Step 5: per-record atomicity sanity check. ---------------------- #
    for old in (old1, old2):
        r = requests.get(f"{POSTS_URL}/{old['id']}", timeout=10)
        assert r.status_code == 404, (
            f"Direct GET {POSTS_URL}/{old['id']} expected 404 after archive, "
            f"got {r.status_code}: {r.text}"
        )
    r = requests.get(f"{ARCHIVE_URL}/{fresh_id}", timeout=10)
    assert r.status_code == 404, (
        f"Direct GET {ARCHIVE_URL}/{fresh_id} expected 404 (fresh post must "
        f"not exist in archive), got {r.status_code}: {r.text}"
    )
