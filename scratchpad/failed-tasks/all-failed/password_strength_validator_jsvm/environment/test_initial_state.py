import os
import shutil
import subprocess
import time

import pytest
import requests

PROJECT_DIR = "/home/user/pb-app"
PB_HOOKS_DIR = os.path.join(PROJECT_DIR, "pb_hooks")
PB_DATA_DIR = os.path.join(PROJECT_DIR, "pb_data")
PB_URL = os.environ.get("PB_URL", "http://127.0.0.1:8090")
PB_ADMIN_EMAIL = os.environ.get("PB_ADMIN_EMAIL", "admin@example.com")
PB_ADMIN_PASSWORD = os.environ.get("PB_ADMIN_PASSWORD", "Admin1234!Pass")
PB_LOG_FILE = "/tmp/pocketbase.log"


def _is_healthy(timeout_sec: float = 2.0) -> bool:
    try:
        r = requests.get(f"{PB_URL}/api/health", timeout=timeout_sec)
        return r.status_code == 200
    except Exception:
        return False


def _wait_for_health(timeout_sec: float = 60.0) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if _is_healthy():
            return True
        time.sleep(1)
    return False


def _start_pocketbase_background():
    log_fd = open(PB_LOG_FILE, "ab")
    subprocess.Popen(
        ["pocketbase", "serve", "--http=0.0.0.0:8090", "--dir", PB_DATA_DIR,
         "--hooksDir", PB_HOOKS_DIR, "--migrationsDir",
         os.path.join(PROJECT_DIR, "pb_migrations")],
        cwd=PROJECT_DIR,
        stdout=log_fd,
        stderr=log_fd,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
    )


@pytest.fixture(scope="session", autouse=True)
def ensure_pocketbase_running():
    """Start PocketBase in the background if not already running, then wait until healthy."""
    if not _is_healthy():
        _start_pocketbase_background()
    assert _wait_for_health(timeout_sec=90.0), (
        f"PocketBase server at {PB_URL} did not become healthy. "
        f"See {PB_LOG_FILE} for details."
    )
    yield


def _superuser_token() -> str:
    r = requests.post(
        f"{PB_URL}/api/collections/_superusers/auth-with-password",
        json={"identity": PB_ADMIN_EMAIL, "password": PB_ADMIN_PASSWORD},
        timeout=15,
    )
    assert r.status_code == 200, (
        f"Failed to authenticate as superuser ({PB_ADMIN_EMAIL}): "
        f"{r.status_code} {r.text}"
    )
    data = r.json()
    token = data.get("token")
    assert token, f"Superuser auth response missing token: {data}"
    return token


def test_pocketbase_binary_available():
    assert shutil.which("pocketbase") is not None, (
        "pocketbase binary not found in PATH; expected v0.31.0 to be installed."
    )


def test_pocketbase_version_is_v0_31():
    out = subprocess.run(
        ["pocketbase", "--version"], capture_output=True, text=True, timeout=15
    )
    combined = (out.stdout or "") + (out.stderr or "")
    assert "0.31" in combined, (
        f"Expected PocketBase v0.31.x, got: {combined.strip()!r}"
    )


def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR), (
        f"Project directory {PROJECT_DIR} does not exist."
    )


def test_pb_hooks_directory_exists():
    assert os.path.isdir(PB_HOOKS_DIR), (
        f"pb_hooks directory {PB_HOOKS_DIR} does not exist."
    )


def test_pocketbase_server_is_reachable():
    assert _wait_for_health(timeout_sec=10.0), (
        f"PocketBase server at {PB_URL} is not reachable."
    )


def test_users_collection_exists_with_email_and_password_fields():
    token = _superuser_token()
    r = requests.get(
        f"{PB_URL}/api/collections/users",
        headers={"Authorization": token},
        timeout=15,
    )
    assert r.status_code == 200, (
        f"Failed to fetch users collection: {r.status_code} {r.text}"
    )
    coll = r.json()
    assert coll.get("type") == "auth", (
        f"Expected users collection of type 'auth', got: {coll.get('type')!r}"
    )
    field_names = {f.get("name") for f in coll.get("fields", []) if isinstance(f, dict)}
    assert "email" in field_names, (
        f"Users collection is missing 'email' field; fields: {sorted(field_names)}"
    )
    assert "password" in field_names, (
        f"Users collection is missing 'password' field; fields: {sorted(field_names)}"
    )


def test_users_collection_allows_public_create():
    token = _superuser_token()
    r = requests.get(
        f"{PB_URL}/api/collections/users",
        headers={"Authorization": token},
        timeout=15,
    )
    assert r.status_code == 200, (
        f"Failed to fetch users collection: {r.status_code} {r.text}"
    )
    coll = r.json()
    create_rule = coll.get("createRule")
    assert create_rule in ("", "true"), (
        f"Expected users.createRule to allow public signup (empty string or 'true'), "
        f"got: {create_rule!r}"
    )
