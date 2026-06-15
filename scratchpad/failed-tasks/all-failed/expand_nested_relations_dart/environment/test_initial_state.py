import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request

import pytest

PROJECT_DIR = "/home/user/myproject"
PB_URL = os.environ.get("PB_URL", "http://127.0.0.1:8090").rstrip("/")
PB_START_SCRIPT = "/usr/local/bin/start-pocketbase.sh"
PB_LOG_PATH = "/tmp/pocketbase.log"


def _http_get(url: str, timeout: float = 2.0) -> int:
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code


def _is_pocketbase_up(attempts: int = 1, delay: float = 0.5) -> bool:
    health = PB_URL + "/api/health"
    for _ in range(attempts):
        try:
            if _http_get(health) == 200:
                return True
        except Exception:
            pass
        if attempts > 1:
            time.sleep(delay)
    return False


def _start_pocketbase_background() -> None:
    if not os.path.isfile(PB_START_SCRIPT):
        return
    log_fh = open(PB_LOG_PATH, "ab", buffering=0)
    subprocess.Popen(
        ["/bin/bash", PB_START_SCRIPT],
        stdout=log_fh,
        stderr=log_fh,
        start_new_session=True,
    )


@pytest.fixture(scope="session", autouse=True)
def _ensure_pocketbase_running():
    if not _is_pocketbase_up(attempts=1):
        _start_pocketbase_background()
    deadline = time.time() + 60
    while time.time() < deadline:
        if _is_pocketbase_up(attempts=1):
            break
        time.sleep(1.0)
    yield


def test_dart_binary_available():
    assert shutil.which("dart") is not None, "dart binary not found in PATH."


def test_pocketbase_binary_available():
    assert shutil.which("pocketbase") is not None, "pocketbase binary not found in PATH."


def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} does not exist."


def test_pocketbase_server_reachable():
    assert _is_pocketbase_up(attempts=30, delay=1.0), (
        f"PocketBase server is not reachable at {PB_URL}/api/health."
    )


@pytest.mark.parametrize("collection", ["users", "categories", "posts", "comments"])
def test_required_collections_exist(collection: str):
    assert _is_pocketbase_up(attempts=30, delay=1.0), (
        f"PocketBase server is not reachable at {PB_URL}/api/health."
    )
    list_url = f"{PB_URL}/api/collections/{collection}/records?perPage=1"
    status = _http_get(list_url, timeout=5.0)
    assert status != 404, (
        f"Required collection '{collection}' does not exist on the PocketBase server."
    )
