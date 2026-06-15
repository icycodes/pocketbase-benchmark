import json
import os
import shutil
import socket
import subprocess
import time

import pytest
import requests

PROJECT_DIR = "/home/user/myproject"
POCKETBASE_DIR = "/home/user/pb"
POCKETBASE_URL = "http://127.0.0.1:8090"
SEED_EMAIL = "harbor-user@example.com"
SEED_PASSWORD = "harbor-pass-1234"
START_SCRIPT = "/usr/local/bin/start-pocketbase.sh"


def _wait_for_port(host: str, port: int, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except OSError:
            time.sleep(0.5)
    return False


def _ensure_pocketbase_running():
    if _wait_for_port("127.0.0.1", 8090, timeout=2.0):
        return
    assert os.path.isfile(START_SCRIPT), (
        f"PocketBase startup script {START_SCRIPT} is missing."
    )
    subprocess.Popen(
        ["bash", START_SCRIPT],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    assert _wait_for_port("127.0.0.1", 8090, timeout=60.0), (
        "PocketBase failed to start on 127.0.0.1:8090."
    )
    # Give the startup script time to seed the user.
    deadline = time.time() + 30.0
    while time.time() < deadline:
        try:
            r = requests.post(
                f"{POCKETBASE_URL}/api/collections/users/auth-with-password",
                json={"identity": SEED_EMAIL, "password": SEED_PASSWORD},
                timeout=5,
            )
            if r.status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(0.5)


def test_node_binary_available():
    assert shutil.which("node") is not None, "node binary not found in PATH."


def test_npm_binary_available():
    assert shutil.which("npm") is not None, "npm binary not found in PATH."


def test_pocketbase_binary_available():
    assert shutil.which("pocketbase") is not None, (
        "pocketbase binary not found in PATH."
    )


def test_pocketbase_version_is_0_31_0():
    result = subprocess.run(
        ["pocketbase", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    combined = (result.stdout or "") + (result.stderr or "")
    assert "0.31.0" in combined, (
        f"Expected PocketBase v0.31.0, got: {combined.strip()!r}"
    )


def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR), (
        f"Project directory {PROJECT_DIR} does not exist."
    )


def test_project_package_json_exists():
    pkg_path = os.path.join(PROJECT_DIR, "package.json")
    assert os.path.isfile(pkg_path), f"{pkg_path} does not exist."
    with open(pkg_path) as f:
        pkg = json.load(f)
    deps = {}
    deps.update(pkg.get("dependencies", {}) or {})
    deps.update(pkg.get("devDependencies", {}) or {})
    assert "pocketbase" in deps, (
        "Expected the 'pocketbase' JS SDK to be listed in package.json dependencies."
    )
    assert any(name.startswith("@sveltejs/kit") or name == "@sveltejs/kit" for name in deps), (
        "Expected @sveltejs/kit to be present in package.json dependencies."
    )


def test_node_modules_installed():
    nm = os.path.join(PROJECT_DIR, "node_modules")
    assert os.path.isdir(nm), (
        f"Expected node_modules to be pre-installed at {nm}."
    )
    pb_sdk = os.path.join(nm, "pocketbase")
    assert os.path.isdir(pb_sdk), (
        "Expected the 'pocketbase' JS SDK to be installed in node_modules."
    )


def test_sveltekit_skeleton_files_exist():
    expected = [
        os.path.join(PROJECT_DIR, "svelte.config.js"),
        os.path.join(PROJECT_DIR, "vite.config.js"),
        os.path.join(PROJECT_DIR, "src"),
        os.path.join(PROJECT_DIR, "src", "routes"),
    ]
    for path in expected:
        assert os.path.exists(path), (
            f"Expected SvelteKit skeleton path {path} to exist."
        )


def test_pocketbase_server_is_running():
    _ensure_pocketbase_running()
    assert _wait_for_port("127.0.0.1", 8090, timeout=30.0), (
        "PocketBase server is not listening on 127.0.0.1:8090."
    )
    resp = requests.get(f"{POCKETBASE_URL}/api/health", timeout=10)
    assert resp.status_code == 200, (
        f"PocketBase /api/health returned {resp.status_code}: {resp.text!r}"
    )


def test_seeded_user_can_authenticate():
    _ensure_pocketbase_running()
    resp = requests.post(
        f"{POCKETBASE_URL}/api/collections/users/auth-with-password",
        json={"identity": SEED_EMAIL, "password": SEED_PASSWORD},
        timeout=10,
    )
    assert resp.status_code == 200, (
        f"Failed to authenticate seeded user {SEED_EMAIL}: "
        f"status={resp.status_code} body={resp.text!r}"
    )
    payload = resp.json()
    assert "token" in payload and payload["token"], (
        "Auth response is missing the 'token' field."
    )
    record = payload.get("record") or {}
    assert record.get("email") == SEED_EMAIL, (
        f"Auth record email mismatch: got {record.get('email')!r}, "
        f"expected {SEED_EMAIL!r}."
    )


def test_sveltekit_preview_port_is_free():
    # The executor will start the preview server on port 4173.
    # Verify nothing else is currently listening on that port.
    try:
        with socket.create_connection(("127.0.0.1", 4173), timeout=1.0):
            listening = True
    except OSError:
        listening = False
    assert not listening, (
        "Port 4173 is already in use; the SvelteKit preview server cannot start."
    )
