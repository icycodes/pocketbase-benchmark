import os
import shutil
import socket
import subprocess
import time

import pytest
import requests

PROJECT_DIR = "/home/user/myproject"
POCKETBASE_BIN = "/home/user/myproject/pocketbase"
TMP_PORT = 18090
HEALTH_URL = f"http://127.0.0.1:{TMP_PORT}/api/health"
COLLECTION_URL = f"http://127.0.0.1:{TMP_PORT}/api/collections/users/records"


def _port_is_free(port: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        try:
            s.bind(("127.0.0.1", port))
        except OSError:
            return False
        return True
    finally:
        s.close()


def _wait_for_url(url: str, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(url, timeout=2)
            if r.status_code < 500:
                return True
        except requests.RequestException:
            pass
        time.sleep(0.5)
    return False


def test_project_dir_exists():
    assert os.path.isdir(PROJECT_DIR), (
        f"Project directory {PROJECT_DIR} does not exist."
    )


def test_pocketbase_binary_available():
    assert os.path.isfile(POCKETBASE_BIN) and os.access(POCKETBASE_BIN, os.X_OK), (
        f"PocketBase binary not found or not executable at {POCKETBASE_BIN}."
    )


def test_pocketbase_version_is_0_31_0():
    out = subprocess.run(
        [POCKETBASE_BIN, "--version"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    combined = (out.stdout or "") + (out.stderr or "")
    assert "0.31.0" in combined, (
        f"Expected PocketBase v0.31.0 binary, got: {combined.strip()!r}"
    )


def test_go_toolchain_available():
    assert shutil.which("go") is not None, (
        "Go toolchain not found in PATH; required to build a custom PocketBase middleware."
    )


def test_pocketbase_reachable_and_users_collection_exists():
    if not _port_is_free(TMP_PORT):
        pytest.skip(f"Port {TMP_PORT} is busy; cannot run initial probe.")

    proc = subprocess.Popen(
        [POCKETBASE_BIN, "serve", "--http", f"127.0.0.1:{TMP_PORT}"],
        cwd=PROJECT_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        assert _wait_for_url(HEALTH_URL, timeout=30.0), (
            f"PocketBase did not become reachable at {HEALTH_URL} within 30s."
        )

        # The users auth collection must be served by PocketBase out of the box.
        # We do not care about list permissions; we only care that the endpoint
        # is wired (i.e., not a 404 "Missing collection" response).
        r = requests.get(COLLECTION_URL, timeout=5)
        assert r.status_code != 404, (
            f"Built-in users collection endpoint {COLLECTION_URL} returned 404; "
            f"the users collection is missing. Body: {r.text!r}"
        )
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
