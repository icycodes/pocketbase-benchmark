import json
import os
import subprocess
import time
import uuid

import pytest
import requests

PROJECT_DIR = "/home/user/myproject"
PB_URL = os.environ.get("PB_URL", "http://127.0.0.1:8090").rstrip("/")
SUPERUSER_EMAIL = os.environ.get("SUPERUSER_EMAIL", "admin@example.com")
SUPERUSER_PASSWORD = os.environ.get("SUPERUSER_PASSWORD", "Admin12345!")
TEST_USER_PASSWORD = "TestPass12345!"


def _wait_for_pocketbase(timeout: float = 60.0) -> None:
    deadline = time.time() + timeout
    last_err: Exception | None = None
    while time.time() < deadline:
        try:
            r = requests.get(f"{PB_URL}/api/health", timeout=2.0)
            if r.status_code == 200:
                return
        except Exception as e:  # noqa: BLE001
            last_err = e
        time.sleep(1.0)
    raise RuntimeError(f"PocketBase server not reachable at {PB_URL}: {last_err}")


def _superuser_token() -> str:
    r = requests.post(
        f"{PB_URL}/api/collections/_superusers/auth-with-password",
        json={"identity": SUPERUSER_EMAIL, "password": SUPERUSER_PASSWORD},
        timeout=10.0,
    )
    assert r.status_code == 200, (
        f"Superuser auth failed: {r.status_code} {r.text}"
    )
    return r.json()["token"]


def _admin_headers(token: str) -> dict[str, str]:
    return {"Authorization": token, "Content-Type": "application/json"}


def _short_id() -> str:
    return uuid.uuid4().hex[:10]


def _create(collection: str, payload: dict, token: str) -> dict:
    r = requests.post(
        f"{PB_URL}/api/collections/{collection}/records",
        json=payload,
        headers=_admin_headers(token),
        timeout=10.0,
    )
    assert r.status_code in (200, 201), (
        f"Create {collection} failed: {r.status_code} {r.text}"
    )
    return r.json()


def _delete_all(collection: str, token: str, filter_expr: str | None = None) -> None:
    params = {"perPage": 200}
    if filter_expr:
        params["filter"] = filter_expr
    r = requests.get(
        f"{PB_URL}/api/collections/{collection}/records",
        params=params,
        headers=_admin_headers(token),
        timeout=10.0,
    )
    if r.status_code != 200:
        return
    for rec in r.json().get("items", []):
        requests.delete(
            f"{PB_URL}/api/collections/{collection}/records/{rec['id']}",
            headers=_admin_headers(token),
            timeout=10.0,
        )


@pytest.fixture(scope="module")
def seeded_fixture():
    _wait_for_pocketbase()
    token = _superuser_token()
    tag = _short_id()

    # Categories
    tech_cat = _create(
        "categories",
        {"name": f"Tech-{tag}"},
        token,
    )
    misc_cat = _create(
        "categories",
        {"name": f"Misc-{tag}"},
        token,
    )

    # Users (auth collection)
    def mk_user(prefix: str) -> dict:
        email = f"{prefix}-{tag}@example.com"
        return _create(
            "users",
            {
                "email": email,
                "password": TEST_USER_PASSWORD,
                "passwordConfirm": TEST_USER_PASSWORD,
                "emailVisibility": True,
            },
            token,
        )

    alice = mk_user("alice")
    bob = mk_user("bob")
    carol = mk_user("carol")

    # Posts
    hello_post = _create(
        "posts",
        {
            "title": f"Hello-{tag}",
            "category": tech_cat["id"],
            "author": alice["id"],
        },
        token,
    )
    other_post = _create(
        "posts",
        {
            "title": f"Other-{tag}",
            "category": misc_cat["id"],
            "author": bob["id"],
        },
        token,
    )

    # Comments targeting hello_post with explicit ascending created timestamps.
    # We rely on natural insertion order to drive `created`; insert with a small
    # delay so timestamps strictly increase.
    def mk_comment(content: str, author_id: str, post_id: str) -> dict:
        rec = _create(
            "comments",
            {"content": content, "author": author_id, "post": post_id},
            token,
        )
        time.sleep(1.1)
        return rec

    c_alice = mk_comment(f"first-{tag}", alice["id"], hello_post["id"])
    c_bob = mk_comment(f"second-{tag}", bob["id"], hello_post["id"])
    c_carol = mk_comment(f"third-{tag}", carol["id"], hello_post["id"])

    # A comment on the OTHER post; must not appear in the output.
    c_other = _create(
        "comments",
        {
            "content": f"unrelated-{tag}",
            "author": alice["id"],
            "post": other_post["id"],
        },
        token,
    )

    fixture = {
        "tag": tag,
        "token": token,
        "categories": {"tech": tech_cat, "misc": misc_cat},
        "users": {"alice": alice, "bob": bob, "carol": carol},
        "posts": {"hello": hello_post, "other": other_post},
        "comments": [c_alice, c_bob, c_carol],
        "other_comment": c_other,
    }

    yield fixture

    # Best-effort cleanup
    for col in ("comments", "posts", "categories"):
        _delete_all(col, token, filter_expr=f'created >= ""')


def _run_dart_cli(post_id: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.setdefault("PB_URL", PB_URL)
    # Ensure deps are resolved (no-op if cached).
    subprocess.run(
        ["dart", "pub", "get"],
        cwd=PROJECT_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    return subprocess.run(
        ["dart", "run", "bin/main.dart", post_id],
        cwd=PROJECT_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )


def test_happy_path_returns_sorted_expanded_comments(seeded_fixture):
    hello = seeded_fixture["posts"]["hello"]
    result = _run_dart_cli(hello["id"])
    assert result.returncode == 0, (
        f"Dart CLI exited non-zero: rc={result.returncode}\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )

    stdout = result.stdout
    assert stdout.endswith("\n"), "Stdout must end with a single trailing newline."
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as e:
        pytest.fail(
            f"Stdout is not a single JSON document: {e}\nSTDOUT:\n{stdout}"
        )

    assert isinstance(data, list), f"Top-level JSON must be a list, got {type(data).__name__}"
    assert len(data) == 3, (
        f"Expected exactly 3 comments for the hello post, got {len(data)}: {data}"
    )

    expected_ids = [c["id"] for c in seeded_fixture["comments"]]
    actual_ids = [item.get("id") for item in data]
    assert actual_ids == expected_ids, (
        f"Comments must be sorted ascending by created. "
        f"Expected {expected_ids}, got {actual_ids}"
    )

    other_comment_id = seeded_fixture["other_comment"]["id"]
    assert other_comment_id not in actual_ids, (
        f"Unrelated comment {other_comment_id} should not appear in the output."
    )

    tech_cat = seeded_fixture["categories"]["tech"]
    users_by_id = {u["id"]: u for u in seeded_fixture["users"].values()}

    for item, expected_comment in zip(data, seeded_fixture["comments"]):
        assert set(item.keys()) == {"id", "content", "author", "post"}, (
            f"Top-level keys must be exactly id/content/author/post, got {sorted(item.keys())}"
        )
        assert item["id"] == expected_comment["id"]
        assert item["content"] == expected_comment["content"]

        author = item["author"]
        assert isinstance(author, dict), "author must be an object"
        assert set(author.keys()) == {"id", "email"}, (
            f"author keys must be exactly id/email, got {sorted(author.keys())}"
        )
        assert author["id"] == expected_comment["author"]
        expected_email = users_by_id[expected_comment["author"]]["email"]
        assert author["email"] == expected_email, (
            f"author.email mismatch: expected {expected_email}, got {author['email']}"
        )

        post = item["post"]
        assert isinstance(post, dict), "post must be an object"
        assert set(post.keys()) == {"id", "title", "category"}, (
            f"post keys must be exactly id/title/category, got {sorted(post.keys())}"
        )
        assert post["id"] == seeded_fixture["posts"]["hello"]["id"]
        assert post["title"] == seeded_fixture["posts"]["hello"]["title"]

        category = post["category"]
        assert isinstance(category, dict), "post.category must be an object"
        assert set(category.keys()) == {"id", "name"}, (
            f"post.category keys must be exactly id/name, got {sorted(category.keys())}"
        )
        assert category["id"] == tech_cat["id"]
        assert category["name"] == tech_cat["name"]


def test_unknown_post_returns_empty_array(seeded_fixture):
    result = _run_dart_cli("nonexistent00")
    assert result.returncode == 0, (
        f"Dart CLI must exit 0 for an unknown post id, got rc={result.returncode}\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert result.stdout == "[]\n", (
        f"Stdout for an unknown post id must be exactly '[]\\n', got: {result.stdout!r}"
    )


def test_stdout_is_single_json_document(seeded_fixture):
    hello = seeded_fixture["posts"]["hello"]
    result = _run_dart_cli(hello["id"])
    assert result.returncode == 0
    body = result.stdout.rstrip("\n")
    # Exactly one JSON document — no extra log lines.
    decoder = json.JSONDecoder()
    obj, idx = decoder.raw_decode(body)
    assert idx == len(body), (
        f"Stdout must contain a single JSON document only; trailing data: {body[idx:]!r}"
    )
    assert isinstance(obj, list)
