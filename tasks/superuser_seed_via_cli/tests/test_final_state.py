import os
import shutil
import socket
import subprocess
import time

import pytest
import requests

PROJECT_DIR = "/home/user/myproject"
SETUP_SCRIPT = os.path.join(PROJECT_DIR, "setup.sh")
POCKETBASE_BINARY = os.path.join(PROJECT_DIR, "pocketbase")
PB_DATA_DIR = os.path.join(PROJECT_DIR, "pb_data")
PB_MIGRATIONS_DIR = os.path.join(PROJECT_DIR, "pb_migrations")

BASE_URL = "http://127.0.0.1:8090"
HEALTH_URL = f"{BASE_URL}/api/health"
AUTH_URL = f"{BASE_URL}/api/collections/_superusers/auth-with-password"
SUPERUSERS_URL = f"{BASE_URL}/api/collections/_superusers/records"
TASKS_COLLECTION_URL = f"{BASE_URL}/api/collections/tasks"
TASKS_RECORDS_URL = f"{BASE_URL}/api/collections/tasks/records"

SUPERUSER_EMAIL = "admin@example.com"
SUPERUSER_PASSWORD = "Adm1n_passw0rd!"

EXPECTED_TASK_TITLES = {
    "Buy groceries",
    "Walk the dog",
    "Read a book",
    "Write weekly report",
    "Call mom",
}


def _stop_any_running_server():
    """Best-effort: kill any leftover pocketbase server that may be running."""
    for cmd in (
        ["pkill", "-f", "pocketbase serve"],
        ["pkill", "-f", "./pocketbase"],
    ):
        if shutil.which(cmd[0]) is None:
            continue
        subprocess.run(cmd, capture_output=True)
    # Give the OS a moment to release port 8090.
    for _ in range(20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", 8090)) != 0:
                return
        time.sleep(0.5)


def _wait_for_health(timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(HEALTH_URL, timeout=2)
            if r.status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(0.5)
    return False


@pytest.fixture(scope="session", autouse=True)
def run_setup_twice_and_warm_server():
    """
    Per the truth's Setup section:
      1. Clean any leftover PocketBase state from the initial environment.
      2. Run `bash setup.sh` twice; each invocation must exit 0.
      3. Wait until the server is reachable on port 8090.
    """
    assert os.path.isfile(SETUP_SCRIPT), (
        f"Expected setup.sh to exist at {SETUP_SCRIPT}, but it was not found."
    )

    _stop_any_running_server()
    if os.path.isdir(PB_DATA_DIR):
        shutil.rmtree(PB_DATA_DIR)
    if os.path.isdir(PB_MIGRATIONS_DIR):
        shutil.rmtree(PB_MIGRATIONS_DIR)

    # First invocation
    first = subprocess.run(
        ["bash", "setup.sh"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert first.returncode == 0, (
        "First invocation of `bash setup.sh` failed with non-zero exit code "
        f"{first.returncode}.\nstdout:\n{first.stdout}\nstderr:\n{first.stderr}"
    )

    # Give the background server a moment to be ready before re-running.
    assert _wait_for_health(timeout=30), (
        "PocketBase server did not become healthy on http://127.0.0.1:8090 "
        "within 30 seconds after the first invocation."
    )

    # Second invocation — must remain idempotent.
    second = subprocess.run(
        ["bash", "setup.sh"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert second.returncode == 0, (
        "Second invocation of `bash setup.sh` failed with non-zero exit code "
        f"{second.returncode}. The script must be idempotent.\n"
        f"stdout:\n{second.stdout}\nstderr:\n{second.stderr}"
    )

    assert _wait_for_health(timeout=30), (
        "PocketBase server did not become healthy on http://127.0.0.1:8090 "
        "within 30 seconds after the second invocation."
    )

    yield

    _stop_any_running_server()


@pytest.fixture(scope="session")
def admin_token() -> str:
    resp = requests.post(
        AUTH_URL,
        json={"identity": SUPERUSER_EMAIL, "password": SUPERUSER_PASSWORD},
        timeout=10,
    )
    assert resp.status_code == 200, (
        "Superuser authentication failed via POST "
        f"/api/collections/_superusers/auth-with-password. "
        f"Status: {resp.status_code}, body: {resp.text}"
    )
    data = resp.json()
    token = data.get("token")
    assert isinstance(token, str) and token, (
        "Expected a non-empty `token` field in the auth-with-password response, "
        f"got: {data!r}"
    )
    return token


def test_server_is_alive():
    resp = requests.get(HEALTH_URL, timeout=5)
    assert resp.status_code == 200, (
        f"Expected GET {HEALTH_URL} to return 200, got {resp.status_code}: "
        f"{resp.text}"
    )
    body = resp.json()
    assert body.get("code") == 200, (
        f"Expected the health response JSON to contain `code: 200`, got: {body!r}"
    )


def test_superuser_authentication_works(admin_token: str):
    # If the fixture succeeded we already have a token; assert it is non-empty.
    assert admin_token, "Superuser admin token must be non-empty."


def test_exactly_one_superuser_exists(admin_token: str):
    resp = requests.get(
        SUPERUSERS_URL,
        params={"perPage": 200},
        headers={"Authorization": admin_token},
        timeout=10,
    )
    assert resp.status_code == 200, (
        f"Expected GET {SUPERUSERS_URL} to return 200, "
        f"got {resp.status_code}: {resp.text}"
    )
    data = resp.json()
    assert data.get("totalItems") == 1, (
        "Expected exactly 1 superuser record after running setup.sh twice, "
        f"got totalItems={data.get('totalItems')}. Full response: {data!r}"
    )
    items = data.get("items", [])
    assert len(items) == 1, (
        f"Expected exactly 1 item in the _superusers list, got {len(items)}: {items!r}"
    )
    assert items[0].get("email") == SUPERUSER_EMAIL, (
        f"Expected the single superuser to have email {SUPERUSER_EMAIL!r}, "
        f"got: {items[0].get('email')!r}"
    )


def test_tasks_collection_schema(admin_token: str):
    resp = requests.get(
        TASKS_COLLECTION_URL,
        headers={"Authorization": admin_token},
        timeout=10,
    )
    assert resp.status_code == 200, (
        f"Expected GET {TASKS_COLLECTION_URL} to return 200, "
        f"got {resp.status_code}: {resp.text}"
    )
    data = resp.json()
    assert data.get("name") == "tasks", (
        f"Expected collection name 'tasks', got: {data.get('name')!r}"
    )
    assert data.get("type") == "base", (
        f"Expected collection type 'base', got: {data.get('type')!r}"
    )
    fields = data.get("fields") or data.get("schema") or []
    field_by_name = {f.get("name"): f for f in fields}

    title_field = field_by_name.get("title")
    assert title_field is not None, (
        f"Expected a 'title' field in the tasks collection schema, got fields: "
        f"{[f.get('name') for f in fields]!r}"
    )
    assert title_field.get("type") == "text", (
        f"Expected 'title' field type 'text', got: {title_field.get('type')!r}"
    )
    assert title_field.get("required") is True, (
        f"Expected 'title' field to be required=true, got: {title_field!r}"
    )

    done_field = field_by_name.get("done")
    assert done_field is not None, (
        "Expected a 'done' field in the tasks collection schema."
    )
    assert done_field.get("type") == "bool", (
        f"Expected 'done' field type 'bool', got: {done_field.get('type')!r}"
    )

    due_field = field_by_name.get("due")
    assert due_field is not None, (
        "Expected a 'due' field in the tasks collection schema."
    )
    assert due_field.get("type") == "date", (
        f"Expected 'due' field type 'date', got: {due_field.get('type')!r}"
    )


def test_exactly_five_seeded_tasks(admin_token: str):
    resp = requests.get(
        TASKS_RECORDS_URL,
        params={"perPage": 200, "sort": "title"},
        headers={"Authorization": admin_token},
        timeout=10,
    )
    assert resp.status_code == 200, (
        f"Expected GET {TASKS_RECORDS_URL} to return 200, "
        f"got {resp.status_code}: {resp.text}"
    )
    data = resp.json()
    assert data.get("totalItems") == 5, (
        "Expected exactly 5 records in the tasks collection after running "
        f"setup.sh twice, got totalItems={data.get('totalItems')}. "
        f"Full response: {data!r}"
    )
    items = data.get("items", [])
    titles = [item.get("title") for item in items]
    assert len(titles) == 5, (
        f"Expected exactly 5 task records returned, got {len(titles)}: {titles!r}"
    )
    assert set(titles) == EXPECTED_TASK_TITLES, (
        "Expected the set of task titles to match the predefined seed list "
        f"{sorted(EXPECTED_TASK_TITLES)!r}, but got {sorted(titles)!r}."
    )
    # No duplicates: a set of 5 unique titles equals the list size.
    assert len(set(titles)) == 5, (
        f"Expected 5 unique task titles, got duplicates: {titles!r}"
    )
