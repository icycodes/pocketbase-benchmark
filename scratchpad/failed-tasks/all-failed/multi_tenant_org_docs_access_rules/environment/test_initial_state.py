"""Initial-state verification for the PocketBase multi-tenant task.

This test runs BEFORE the agent attempts the task. It verifies that:
  * the PocketBase v0.31.0 binary is installed inside the project directory,
  * the expected project directory layout exists,
  * the PocketBase server can be started non-interactively on 0.0.0.0:8090,
  * the bootstrapped superuser credentials work.

Seeding of the per-tenant fixtures (organizations / memberships / documents)
happens lazily from ``tests/test_final_state.py`` because those collections
are authored by the agent during task execution and therefore do not yet
exist at this point in the lifecycle.
"""

import os
import shutil
import socket
import subprocess
import time

import pytest
import urllib.request
import urllib.error
import json

PROJECT_DIR = "/home/user/myproject"
POCKETBASE_BIN = os.path.join(PROJECT_DIR, "pocketbase")
PB_DATA_DIR = os.path.join(PROJECT_DIR, "pb_data")
PB_MIGRATIONS_DIR = os.path.join(PROJECT_DIR, "pb_migrations")
PB_BASE_URL = "http://127.0.0.1:8090"
SUPERUSER_EMAIL = "admin@example.com"
SUPERUSER_PASSWORD = "Adm1n_Password!"


def _port_open(host: str, port: int) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.5)
    try:
        return sock.connect_ex((host, port)) == 0
    finally:
        sock.close()


def _http_json(method: str, url: str, body: dict | None = None, token: str | None = None, timeout: float = 5.0):
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = token
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8") or "null")
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read().decode("utf-8") or "null")
        except Exception:
            payload = None
        return e.code, payload


def _wait_for_health(timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            status, _ = _http_json("GET", f"{PB_BASE_URL}/api/health", timeout=2.0)
            if status == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def _start_server_if_needed() -> None:
    if _port_open("127.0.0.1", 8090):
        return
    log_path = os.path.join(PROJECT_DIR, "pocketbase-server.log")
    log_file = open(log_path, "ab", buffering=0)
    subprocess.Popen(
        [
            POCKETBASE_BIN,
            "serve",
            "--http=0.0.0.0:8090",
            f"--dir={PB_DATA_DIR}",
            f"--migrationsDir={PB_MIGRATIONS_DIR}",
        ],
        cwd=PROJECT_DIR,
        stdout=log_file,
        stderr=log_file,
        close_fds=True,
    )
    assert _wait_for_health(timeout=30.0), (
        f"PocketBase server did not become healthy on {PB_BASE_URL} within 30s; "
        f"see {log_path}."
    )


def test_pocketbase_binary_present():
    assert os.path.isfile(POCKETBASE_BIN), (
        f"Expected PocketBase binary at {POCKETBASE_BIN}, but it was not found."
    )
    assert os.access(POCKETBASE_BIN, os.X_OK), (
        f"PocketBase binary at {POCKETBASE_BIN} is not executable."
    )


def test_project_directory_layout():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} is missing."
    assert os.path.isdir(PB_DATA_DIR), (
        f"PocketBase data directory {PB_DATA_DIR} is missing; the superuser bootstrap "
        "did not run during image build."
    )
    assert os.path.isdir(PB_MIGRATIONS_DIR), (
        f"PocketBase migrations directory {PB_MIGRATIONS_DIR} is missing."
    )


def test_pocketbase_version_is_v031():
    result = subprocess.run(
        [POCKETBASE_BIN, "--version"],
        capture_output=True,
        text=True,
        timeout=10,
        cwd=PROJECT_DIR,
    )
    assert result.returncode == 0, (
        f"`pocketbase --version` failed with code {result.returncode}: {result.stderr}"
    )
    stdout = (result.stdout or "") + (result.stderr or "")
    assert "v0.31.0" in stdout, (
        f"Expected PocketBase v0.31.0, got: {stdout.strip()!r}"
    )


def test_curl_available():
    # curl is used by some agents and by downstream tests; assert it is reachable.
    assert shutil.which("curl") is not None, "curl is required but not found on PATH."


def test_server_can_start_and_is_healthy():
    _start_server_if_needed()
    status, payload = _http_json("GET", f"{PB_BASE_URL}/api/health", timeout=5.0)
    assert status == 200, (
        f"Expected /api/health to return 200, got {status} with payload {payload!r}."
    )


def test_bootstrapped_superuser_can_authenticate():
    _start_server_if_needed()
    status, payload = _http_json(
        "POST",
        f"{PB_BASE_URL}/api/collections/_superusers/auth-with-password",
        body={"identity": SUPERUSER_EMAIL, "password": SUPERUSER_PASSWORD},
        timeout=10.0,
    )
    assert status == 200, (
        f"Bootstrapped superuser auth failed with status {status}: {payload!r}. "
        "The Dockerfile must create a superuser with email "
        f"{SUPERUSER_EMAIL!r} and the documented password."
    )
    assert isinstance(payload, dict) and payload.get("token"), (
        f"Superuser auth response is missing a token: {payload!r}"
    )
