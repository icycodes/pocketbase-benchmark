import json
import os
import shutil
import signal
import socket
import subprocess
import time

import pytest
import requests

PROJECT_DIR = "/home/user/myproject"
BINARY_PATH = os.path.join(PROJECT_DIR, "app")
PB_DATA_DIR = os.path.join(PROJECT_DIR, "pb_data")
BASE_URL = "http://localhost:8090"
PORT = 8090


def _wait_for_port(host: str, port: int, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1.0)
            try:
                if s.connect_ex((host, port)) == 0:
                    return True
            except OSError:
                pass
        time.sleep(0.5)
    return False


def _stop_process(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    try:
        proc.send_signal(signal.SIGINT)
        try:
            proc.wait(timeout=10)
            return
        except subprocess.TimeoutExpired:
            pass
        proc.terminate()
        try:
            proc.wait(timeout=10)
            return
        except subprocess.TimeoutExpired:
            pass
        proc.kill()
        proc.wait(timeout=5)
    except Exception:
        pass


def _start_serve() -> subprocess.Popen:
    proc = subprocess.Popen(
        [BINARY_PATH, "serve", "--http=0.0.0.0:8090"],
        cwd=PROJECT_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert _wait_for_port("localhost", PORT, timeout=30), (
        "PocketBase serve did not start listening on port 8090 within 30 seconds."
    )
    # small buffer to ensure routes are registered
    time.sleep(0.5)
    return proc


def _run_cli(args, check_code: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(
        [BINARY_PATH, *args],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    )
    if check_code:
        assert result.returncode == 0, (
            f"`./app {' '.join(args)}` failed with code {result.returncode}: "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )
    return result


def _build_binary() -> None:
    result = subprocess.run(
        ["go", "build", "-o", BINARY_PATH, "."],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"`go build` failed: stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert os.path.isfile(BINARY_PATH), (
        f"Expected built binary at {BINARY_PATH} but it does not exist."
    )


def _bootstrap_superuser() -> None:
    email = os.environ.get("PB_SUPERUSER_EMAIL", "admin@example.com")
    password = os.environ.get("PB_SUPERUSER_PASSWORD", "Admin123!Admin123!")
    # `superuser upsert` is idempotent and available in v0.31.0.
    subprocess.run(
        [BINARY_PATH, "superuser", "upsert", email, password],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    )


@pytest.fixture(scope="module", autouse=True)
def _setup_clean_environment():
    # Wipe any stale pb_data so migrations apply from scratch.
    if os.path.isdir(PB_DATA_DIR):
        shutil.rmtree(PB_DATA_DIR)
    _build_binary()
    _bootstrap_superuser()
    yield
    # Best-effort cleanup.
    if os.path.isdir(PB_DATA_DIR):
        shutil.rmtree(PB_DATA_DIR, ignore_errors=True)


# Cache state shared across ordered tests.
STATE: dict = {}


def test_01_migrate_up_succeeds():
    result = _run_cli(["migrate", "up"])
    combined = (result.stdout or "") + (result.stderr or "")
    assert combined.strip() != "", (
        "`./app migrate up` produced no output; expected at least one applied "
        f"migration line. stdout={result.stdout!r} stderr={result.stderr!r}"
    )


def test_02_categories_collection_has_three_seeded_records():
    proc = _start_serve()
    try:
        resp = requests.get(
            f"{BASE_URL}/api/collections/categories/records",
            params={"perPage": 50},
            timeout=10,
        )
        assert resp.status_code == 200, (
            f"GET /api/collections/categories/records returned "
            f"{resp.status_code}: {resp.text!r}"
        )
        body = resp.json()
        assert body.get("totalItems") == 3, (
            f"Expected totalItems == 3 for categories, got {body.get('totalItems')}. "
            f"Body: {body!r}"
        )
        items = body.get("items", [])
        names = sorted([item.get("name") for item in items])
        assert names == ["Life", "News", "Tech"], (
            f"Expected category names {{Tech, Life, News}}, got {names!r}"
        )
        STATE["category_ids"] = sorted([item["id"] for item in items])
        STATE["category_name_to_id"] = {item["name"]: item["id"] for item in items}
    finally:
        _stop_process(proc)


def test_03_articles_collection_has_six_seeded_records():
    proc = _start_serve()
    try:
        resp = requests.get(
            f"{BASE_URL}/api/collections/articles/records",
            params={"perPage": 50},
            timeout=10,
        )
        assert resp.status_code == 200, (
            f"GET /api/collections/articles/records returned "
            f"{resp.status_code}: {resp.text!r}"
        )
        body = resp.json()
        assert body.get("totalItems") == 6, (
            f"Expected totalItems == 6 for articles, got {body.get('totalItems')}. "
            f"Body: {body!r}"
        )
        items = body.get("items", [])
        assert len(items) == 6, (
            f"Expected exactly 6 article items, got {len(items)}"
        )
        valid_category_ids = set(STATE.get("category_ids", []))
        assert valid_category_ids, (
            "category_ids not collected from previous test; cannot validate links."
        )
        for art in items:
            cat = art.get("category")
            assert cat in valid_category_ids, (
                f"Article {art.get('id')!r} has category={cat!r} not in "
                f"{valid_category_ids!r}"
            )
            assert isinstance(art.get("title"), str) and art["title"].strip(), (
                f"Article {art.get('id')!r} has empty/non-string title: "
                f"{art.get('title')!r}"
            )
            assert isinstance(art.get("body"), str) and art["body"].strip(), (
                f"Article {art.get('id')!r} has empty/non-string body: "
                f"{art.get('body')!r}"
            )
    finally:
        _stop_process(proc)


def test_04_category_name_field_is_unique():
    proc = _start_serve()
    try:
        # Authenticate as superuser to query collection schema.
        email = os.environ.get("PB_SUPERUSER_EMAIL", "admin@example.com")
        password = os.environ.get("PB_SUPERUSER_PASSWORD", "Admin123!Admin123!")
        auth = requests.post(
            f"{BASE_URL}/api/collections/_superusers/auth-with-password",
            json={"identity": email, "password": password},
            timeout=10,
        )
        assert auth.status_code == 200, (
            f"Superuser auth failed ({auth.status_code}): {auth.text!r}"
        )
        token = auth.json().get("token")
        assert token, f"No token in superuser auth response: {auth.json()!r}"
        headers = {"Authorization": token}

        resp = requests.get(
            f"{BASE_URL}/api/collections/categories",
            headers=headers,
            timeout=10,
        )
        assert resp.status_code == 200, (
            f"GET /api/collections/categories returned {resp.status_code}: "
            f"{resp.text!r}"
        )
        coll = resp.json()
        fields = coll.get("fields", []) or coll.get("schema", [])
        name_field = next((f for f in fields if f.get("name") == "name"), None)
        assert name_field is not None, (
            f"`name` field not found on categories collection. Fields: {fields!r}"
        )
        # Uniqueness can be enforced either by the field-level `unique` attribute
        # or by a UNIQUE INDEX on the collection.
        indexes = coll.get("indexes", [])
        unique_name = bool(name_field.get("unique")) or any(
            "UNIQUE" in idx.upper() and "name" in idx.lower() for idx in indexes
        )
        assert unique_name, (
            "Expected `name` field on categories to be unique (either field-level "
            f"unique=true or a UNIQUE INDEX). field={name_field!r} indexes={indexes!r}"
        )

        STATE["categories_collection_id"] = coll.get("id")
    finally:
        _stop_process(proc)


def test_05_articles_category_relation_required_cascade():
    proc = _start_serve()
    try:
        email = os.environ.get("PB_SUPERUSER_EMAIL", "admin@example.com")
        password = os.environ.get("PB_SUPERUSER_PASSWORD", "Admin123!Admin123!")
        auth = requests.post(
            f"{BASE_URL}/api/collections/_superusers/auth-with-password",
            json={"identity": email, "password": password},
            timeout=10,
        )
        assert auth.status_code == 200, (
            f"Superuser auth failed ({auth.status_code}): {auth.text!r}"
        )
        token = auth.json().get("token")
        headers = {"Authorization": token}

        resp = requests.get(
            f"{BASE_URL}/api/collections/articles",
            headers=headers,
            timeout=10,
        )
        assert resp.status_code == 200, (
            f"GET /api/collections/articles returned {resp.status_code}: "
            f"{resp.text!r}"
        )
        coll = resp.json()
        fields = coll.get("fields", []) or coll.get("schema", [])
        cat_field = next((f for f in fields if f.get("name") == "category"), None)
        assert cat_field is not None, (
            f"`category` field not found on articles collection. Fields: {fields!r}"
        )
        assert cat_field.get("type") == "relation", (
            f"`category` field is not a relation: {cat_field!r}"
        )
        assert cat_field.get("required") is True, (
            f"`category` field must be required, got: {cat_field!r}"
        )
        max_select = cat_field.get("maxSelect")
        assert max_select == 1, (
            f"`category` field must be a single relation (maxSelect=1), got "
            f"maxSelect={max_select!r}"
        )
        assert cat_field.get("cascadeDelete") is True, (
            f"`category` field must have cascadeDelete=true, got: {cat_field!r}"
        )
        expected_cat_id = STATE.get("categories_collection_id")
        assert (
            cat_field.get("collectionId") == expected_cat_id
            and expected_cat_id is not None
        ), (
            f"`category` relation collectionId should be categories collection "
            f"({expected_cat_id!r}), got {cat_field.get('collectionId')!r}"
        )
    finally:
        _stop_process(proc)


def test_06_migrate_down_removes_collections():
    _run_cli(["migrate", "down", "1"])
    proc = _start_serve()
    try:
        cat_resp = requests.get(
            f"{BASE_URL}/api/collections/categories/records", timeout=10
        )
        art_resp = requests.get(
            f"{BASE_URL}/api/collections/articles/records", timeout=10
        )
        assert cat_resp.status_code == 404, (
            f"Expected 404 after down for /api/collections/categories/records, "
            f"got {cat_resp.status_code}: {cat_resp.text!r}"
        )
        assert art_resp.status_code == 404, (
            f"Expected 404 after down for /api/collections/articles/records, "
            f"got {art_resp.status_code}: {art_resp.text!r}"
        )
    finally:
        _stop_process(proc)


def test_07_migrate_up_again_restores_seed_data_deterministically():
    _run_cli(["migrate", "up"])
    proc = _start_serve()
    try:
        cat_resp = requests.get(
            f"{BASE_URL}/api/collections/categories/records",
            params={"perPage": 50},
            timeout=10,
        )
        assert cat_resp.status_code == 200, (
            f"GET categories after re-up returned {cat_resp.status_code}: "
            f"{cat_resp.text!r}"
        )
        cat_body = cat_resp.json()
        assert cat_body.get("totalItems") == 3, (
            f"Expected 3 categories after re-up, got "
            f"{cat_body.get('totalItems')!r}: {cat_body!r}"
        )
        names = sorted([i.get("name") for i in cat_body.get("items", [])])
        assert names == ["Life", "News", "Tech"], (
            f"Expected category names {{Tech, Life, News}} after re-up, got "
            f"{names!r}"
        )
        new_cat_ids = {i["id"] for i in cat_body.get("items", [])}

        art_resp = requests.get(
            f"{BASE_URL}/api/collections/articles/records",
            params={"perPage": 50},
            timeout=10,
        )
        assert art_resp.status_code == 200, (
            f"GET articles after re-up returned {art_resp.status_code}: "
            f"{art_resp.text!r}"
        )
        art_body = art_resp.json()
        assert art_body.get("totalItems") == 6, (
            f"Expected 6 articles after re-up, got "
            f"{art_body.get('totalItems')!r}: {art_body!r}"
        )
        for art in art_body.get("items", []):
            assert art.get("category") in new_cat_ids, (
                f"Article {art.get('id')!r} category={art.get('category')!r} "
                f"not in new category ids {new_cat_ids!r}"
            )
    finally:
        _stop_process(proc)
