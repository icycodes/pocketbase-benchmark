import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request

import pytest


PROJECT_DIR = "/home/user/myproject"
PB_DATA_DIR = "/home/user/pb_data"
PB_URL = "http://127.0.0.1:8090"
PB_LOG = "/tmp/pocketbase.log"
PB_PID_FILE = "/tmp/pocketbase.pid"


# ---------------------------- helpers ----------------------------

def _http_get(url: str, headers: dict | None = None, timeout: float = 5.0):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read().decode("utf-8")


def _http_post_json(url: str, payload: dict, headers: dict | None = None, timeout: float = 10.0):
    body = json.dumps(payload).encode("utf-8")
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=body, headers=h, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")


def _wait_for_health(timeout_sec: float = 30.0) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            status, _ = _http_get(f"{PB_URL}/api/health", timeout=2.0)
            if status == 200:
                return True
        except Exception:
            pass
        time.sleep(0.3)
    return False


def _server_already_running() -> bool:
    try:
        status, _ = _http_get(f"{PB_URL}/api/health", timeout=1.0)
        return status == 200
    except Exception:
        return False


def _bootstrap_superuser() -> None:
    email = os.environ["PB_ADMIN_EMAIL"]
    password = os.environ["PB_ADMIN_PASSWORD"]
    # `pocketbase superuser upsert` is idempotent and non-interactive.
    result = subprocess.run(
        ["pocketbase", "superuser", "upsert", email, password, "--dir", PB_DATA_DIR],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"Failed to bootstrap superuser non-interactively. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )


def _start_pocketbase() -> None:
    if _server_already_running():
        return
    # Launch detached so it survives test process exit.
    log_fd = open(PB_LOG, "ab", buffering=0)
    proc = subprocess.Popen(
        ["pocketbase", "serve", "--http=0.0.0.0:8090", "--dir", PB_DATA_DIR],
        stdout=log_fd,
        stderr=log_fd,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    with open(PB_PID_FILE, "w") as f:
        f.write(str(proc.pid))
    if not _wait_for_health(30):
        with open(PB_LOG, "r", errors="replace") as f:
            log_tail = f.read()[-2000:]
        pytest.fail(f"PocketBase server failed to become healthy. Log tail:\n{log_tail}")


def _superuser_token() -> str:
    email = os.environ["PB_ADMIN_EMAIL"]
    password = os.environ["PB_ADMIN_PASSWORD"]
    status, body = _http_post_json(
        f"{PB_URL}/api/collections/_superusers/auth-with-password",
        {"identity": email, "password": password},
    )
    assert status == 200, f"Superuser auth failed: status={status} body={body}"
    return json.loads(body)["token"]


def _ensure_messages_collection() -> None:
    token = _superuser_token()
    # Idempotent: only create if it does not already exist.
    try:
        status, body = _http_get(
            f"{PB_URL}/api/collections/messages",
            headers={"Authorization": token},
            timeout=5.0,
        )
        if status == 200:
            return
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise

    payload = {
        "name": "messages",
        "type": "base",
        "fields": [
            {"name": "chat", "type": "text", "required": True},
            {"name": "body", "type": "text", "required": False},
        ],
        # Empty rules => publicly accessible for the purposes of this benchmark,
        # which is required so that an unauthenticated SSE client can receive events.
        "listRule": "",
        "viewRule": "",
        "createRule": "",
        "updateRule": "",
        "deleteRule": "",
    }
    status, body = _http_post_json(
        f"{PB_URL}/api/collections",
        payload,
        headers={"Authorization": token},
    )
    assert status in (200, 201), (
        f"Failed to create 'messages' collection: status={status} body={body}"
    )


# ---------------------------- fixtures ----------------------------

@pytest.fixture(scope="session", autouse=True)
def _bootstrap_environment():
    assert os.environ.get("PB_ADMIN_EMAIL"), "PB_ADMIN_EMAIL env var must be set."
    assert os.environ.get("PB_ADMIN_PASSWORD"), "PB_ADMIN_PASSWORD env var must be set."

    os.makedirs(PB_DATA_DIR, exist_ok=True)
    _bootstrap_superuser()
    _start_pocketbase()
    _ensure_messages_collection()
    yield


# ---------------------------- tests ----------------------------

def test_pocketbase_binary_available():
    assert shutil.which("pocketbase") is not None, (
        "pocketbase binary not found in PATH. The PocketBase v0.31.0 binary must be installed."
    )


def test_pocketbase_server_version():
    """Verify the installed PocketBase server is v0.31.0."""
    result = subprocess.run(
        ["pocketbase", "--version"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, f"`pocketbase --version` failed: {result.stderr!r}"
    out = (result.stdout + result.stderr).strip()
    assert "0.31.0" in out, f"Expected PocketBase v0.31.0, got: {out!r}"


def test_node_binary_available():
    assert shutil.which("node") is not None, "node binary not found in PATH."


def test_npm_binary_available():
    assert shutil.which("npm") is not None, "npm binary not found in PATH."


def test_project_dir_exists():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} does not exist."


def test_admin_env_vars_present():
    assert os.environ.get("PB_ADMIN_EMAIL"), "PB_ADMIN_EMAIL env var must be set."
    assert os.environ.get("PB_ADMIN_PASSWORD"), "PB_ADMIN_PASSWORD env var must be set."


def test_pocketbase_server_is_running():
    assert _wait_for_health(15.0), (
        f"PocketBase server is not reachable at {PB_URL}/api/health"
    )


def test_messages_collection_exists():
    token = _superuser_token()
    status, body = _http_get(
        f"{PB_URL}/api/collections/messages",
        headers={"Authorization": token},
    )
    assert status == 200, f"messages collection lookup failed: status={status} body={body}"
    data = json.loads(body)
    field_names = {f.get("name") for f in data.get("fields", [])}
    assert "chat" in field_names, f"messages collection is missing 'chat' field. fields={field_names}"
    assert "body" in field_names, f"messages collection is missing 'body' field. fields={field_names}"


def test_subscribe_script_not_yet_created():
    # The agent is expected to create subscribe.js; it must not exist at initial state.
    path = os.path.join(PROJECT_DIR, "subscribe.js")
    assert not os.path.exists(path), (
        f"{path} must not exist at initial state; the agent is expected to create it."
    )
