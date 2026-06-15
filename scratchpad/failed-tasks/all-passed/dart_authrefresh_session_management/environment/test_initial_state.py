import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request

PROJECT_DIR = "/home/user/myproject"
PB_BASE_URL = "http://127.0.0.1:8090"
SEED_EMAIL = "user@example.com"
SEED_PASSWORD = "password"


def _is_pocketbase_healthy(timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(f"{PB_BASE_URL}/api/health", timeout=timeout) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, ConnectionError):
        return False


def _ensure_pocketbase_running():
    if _is_pocketbase_healthy():
        return
    # Start the server detached so it survives this pytest session.
    subprocess.run(
        ["/usr/local/bin/start_pocketbase.sh"],
        check=True,
        timeout=60,
    )
    deadline = time.time() + 60
    while time.time() < deadline:
        if _is_pocketbase_healthy():
            return
        time.sleep(0.5)
    raise RuntimeError("PocketBase server did not become healthy in time.")


def test_dart_binary_available():
    assert shutil.which("dart") is not None, (
        "dart binary not found in PATH; the Dart SDK must be installed."
    )


def test_dart_sdk_runs():
    result = subprocess.run(
        ["dart", "--version"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"`dart --version` failed with exit code {result.returncode}: "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )


def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR), (
        f"Expected project directory {PROJECT_DIR} to exist before the task starts."
    )


def test_pocketbase_server_is_running():
    _ensure_pocketbase_running()
    with urllib.request.urlopen(f"{PB_BASE_URL}/api/health", timeout=10) as resp:
        assert resp.status == 200, (
            f"Expected PocketBase health endpoint to return 200, got {resp.status}."
        )
        body = json.loads(resp.read().decode("utf-8"))
    assert body.get("code") == 200, (
        f"Expected PocketBase health body to include code=200, got {body!r}."
    )


def test_seed_user_can_authenticate():
    _ensure_pocketbase_running()
    payload = json.dumps(
        {"identity": SEED_EMAIL, "password": SEED_PASSWORD}
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{PB_BASE_URL}/api/collections/users/auth-with-password",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        assert resp.status == 200, (
            f"Expected seed user auth to return 200, got {resp.status}."
        )
        body = json.loads(resp.read().decode("utf-8"))
    assert isinstance(body.get("token"), str) and body["token"], (
        "Expected seed user authentication to return a non-empty token."
    )
    record = body.get("record") or {}
    assert record.get("email") == SEED_EMAIL, (
        f"Expected seed user email to be {SEED_EMAIL}, got {record.get('email')!r}."
    )
