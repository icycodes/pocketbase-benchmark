import glob
import os
import socket
import time

import pytest
import requests
from xprocess import ProcessStarter

PROJECT_DIR = "/home/user/myproject"
HOOKS_DIR = os.path.join(PROJECT_DIR, "pb_hooks")
BASE_URL = "http://127.0.0.1:8090"

PB_PORT = 8090
PASSWORD = "Test123Password!"


def _run_id() -> str:
    run_id = os.environ.get("ZEALT_RUN_ID")
    assert run_id, "ZEALT_RUN_ID environment variable is required."
    return run_id


def _superuser_email() -> str:
    email = os.environ.get("PB_SUPERUSER_EMAIL")
    assert email, "PB_SUPERUSER_EMAIL must be set in the environment."
    return email


def _superuser_password() -> str:
    pw = os.environ.get("PB_SUPERUSER_PASSWORD")
    assert pw, "PB_SUPERUSER_PASSWORD must be set in the environment."
    return pw


@pytest.fixture(scope="session")
def start_pocketbase(xprocess):
    class Starter(ProcessStarter):
        name = "start_pocketbase"
        args = ["./pocketbase", "serve", "--http=0.0.0.0:8090"]
        env = os.environ.copy()
        popen_kwargs = {
            "cwd": PROJECT_DIR,
            "text": True,
        }
        timeout = 60
        terminate_on_interrupt = True

        def startup_check(self):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(2)
                    if s.connect_ex(("127.0.0.1", PB_PORT)) != 0:
                        return False
                resp = requests.get(f"{BASE_URL}/api/health", timeout=5)
                return resp.status_code == 200
            except Exception:
                return False

    xprocess.ensure(Starter.name, Starter)

    # extra readiness wait for /api/health
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            r = requests.get(f"{BASE_URL}/api/health", timeout=2)
            if r.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(0.5)

    yield

    info = xprocess.getinfo(Starter.name)
    info.terminate()


def test_hook_file_exists():
    """A *.pb.js hook file must be present in pb_hooks/."""
    matches = glob.glob(os.path.join(HOOKS_DIR, "*.pb.js"))
    assert matches, (
        f"Expected at least one '*.pb.js' hook file under {HOOKS_DIR}, found none."
    )


def test_sanitization_on_dirty_email(start_pocketbase):
    """A mixed-case, whitespace-padded email must be persisted as trimmed + lowercase."""
    run_id = _run_id()
    dirty_email = f"  HARBOR-Sanitize-{run_id}@Example.COM  "
    expected_email = f"harbor-sanitize-{run_id}@example.com"

    create_resp = requests.post(
        f"{BASE_URL}/api/collections/users/records",
        json={
            "email": dirty_email,
            "password": PASSWORD,
            "passwordConfirm": PASSWORD,
        },
        timeout=15,
    )
    assert create_resp.status_code == 200, (
        "Expected HTTP 200 when creating a user with a dirty email, got "
        f"{create_resp.status_code}: {create_resp.text}"
    )

    auth_resp = requests.post(
        f"{BASE_URL}/api/collections/users/auth-with-password",
        json={"identity": expected_email, "password": PASSWORD},
        timeout=15,
    )
    assert auth_resp.status_code == 200, (
        "Expected the sanitized (lowercase, trimmed) email to authenticate "
        "successfully (proves it was stored after sanitization). Got "
        f"{auth_resp.status_code}: {auth_resp.text}"
    )

    data = auth_resp.json()
    stored_email = data.get("record", {}).get("email")
    assert stored_email == expected_email, (
        "Expected stored email to be "
        f"{expected_email!r} after sanitization, got {stored_email!r}."
    )


def test_sanitization_idempotent_on_clean_email(start_pocketbase):
    """An already-clean email must be accepted and stored unchanged."""
    run_id = _run_id()
    clean_email = f"harbor-clean-{run_id}@example.com"

    create_resp = requests.post(
        f"{BASE_URL}/api/collections/users/records",
        json={
            "email": clean_email,
            "password": PASSWORD,
            "passwordConfirm": PASSWORD,
        },
        timeout=15,
    )
    assert create_resp.status_code == 200, (
        "Expected HTTP 200 when creating a user with an already-clean email, "
        f"got {create_resp.status_code}: {create_resp.text}"
    )

    auth_resp = requests.post(
        f"{BASE_URL}/api/collections/users/auth-with-password",
        json={"identity": clean_email, "password": PASSWORD},
        timeout=15,
    )
    assert auth_resp.status_code == 200, (
        "Expected the clean email to authenticate successfully, got "
        f"{auth_resp.status_code}: {auth_resp.text}"
    )
    data = auth_resp.json()
    stored_email = data.get("record", {}).get("email")
    assert stored_email == clean_email, (
        "Expected the already-clean email to be stored unchanged. "
        f"Expected {clean_email!r}, got {stored_email!r}."
    )


def test_superusers_collection_not_affected(start_pocketbase):
    """The hook must only target the 'users' collection."""
    su_email = _superuser_email()
    su_password = _superuser_password()

    auth_resp = requests.post(
        f"{BASE_URL}/api/collections/_superusers/auth-with-password",
        json={"identity": su_email, "password": su_password},
        timeout=15,
    )
    assert auth_resp.status_code == 200, (
        "Pre-created superuser must still be able to log in via "
        "/_superusers/auth-with-password. The hook should target 'users' only. "
        f"Got HTTP {auth_resp.status_code}: {auth_resp.text}"
    )

    data = auth_resp.json()
    stored_email = data.get("record", {}).get("email")
    assert stored_email == su_email, (
        "Superuser email must be stored exactly as originally configured. "
        f"Expected {su_email!r}, got {stored_email!r}. "
        "This means the hook is incorrectly mutating non-`users` collections."
    )
