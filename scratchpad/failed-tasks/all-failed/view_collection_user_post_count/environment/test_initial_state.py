import os
import shutil
import socket
import subprocess
import time

import pytest
import requests

PROJECT_DIR = "/home/user/myproject"
PB_HOST = "127.0.0.1"
PB_PORT = 8090
PB_BASE_URL = f"http://{PB_HOST}:{PB_PORT}"


def _wait_for_port(host: str, port: int, timeout: float = 180.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1.0)
            try:
                if s.connect_ex((host, port)) == 0:
                    return True
            except OSError:
                pass
        time.sleep(1.0)
    return False


def _server_already_running() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        try:
            return s.connect_ex((PB_HOST, PB_PORT)) == 0
        except OSError:
            return False


@pytest.fixture(scope="module", autouse=True)
def pocketbase_server():
    """Apply migrations, ensure a superuser exists, and start the PocketBase
    server in the background so the rest of the initial-state tests (and the
    executor that runs afterwards) can talk to it."""
    email = os.environ.get("POCKETBASE_SUPERUSER_EMAIL")
    password = os.environ.get("POCKETBASE_SUPERUSER_PASSWORD")
    assert email, "POCKETBASE_SUPERUSER_EMAIL env var must be provided."
    assert password, "POCKETBASE_SUPERUSER_PASSWORD env var must be provided."

    # 1. Apply Go migrations (creates users + posts collections on first run).
    migrate = subprocess.run(
        ["go", "run", ".", "migrate", "up"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert migrate.returncode == 0, (
        "Initial 'go run . migrate up' failed: "
        f"stdout={migrate.stdout!r} stderr={migrate.stderr!r}"
    )

    # 2. Ensure a superuser exists for API-based verification.
    upsert = subprocess.run(
        ["go", "run", ".", "superuser", "upsert", email, password],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert upsert.returncode == 0, (
        "Initial 'superuser upsert' failed: "
        f"stdout={upsert.stdout!r} stderr={upsert.stderr!r}"
    )

    # 3. Start the server in the background, unless one is already running.
    process = None
    if not _server_already_running():
        log_path = "/tmp/pocketbase_initial.log"
        log_file = open(log_path, "w")
        process = subprocess.Popen(
            ["go", "run", ".", "serve", f"--http={PB_HOST}:{PB_PORT}"],
            cwd=PROJECT_DIR,
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )

    assert _wait_for_port(PB_HOST, PB_PORT, timeout=180.0), (
        f"PocketBase did not start listening on {PB_HOST}:{PB_PORT} within 180s."
    )

    yield

    # Intentionally leave the server running so the agent can interact with it.
    # We only clean up if our subprocess crashed early.
    if process is not None and process.poll() is not None:
        process.wait(timeout=5)


def test_go_toolchain_available():
    assert shutil.which("go") is not None, (
        "Go toolchain not found in PATH; the project relies on `go run` to "
        "apply migrations and serve PocketBase."
    )


def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR), (
        f"Expected PocketBase project directory at {PROJECT_DIR}."
    )


def test_project_has_go_module_files():
    go_mod = os.path.join(PROJECT_DIR, "go.mod")
    main_go = os.path.join(PROJECT_DIR, "main.go")
    migrations_dir = os.path.join(PROJECT_DIR, "migrations")
    assert os.path.isfile(go_mod), f"Missing Go module file: {go_mod}."
    assert os.path.isfile(main_go), f"Missing main entrypoint: {main_go}."
    assert os.path.isdir(migrations_dir), (
        f"Missing migrations directory: {migrations_dir}."
    )


def _superuser_token() -> str:
    email = os.environ["POCKETBASE_SUPERUSER_EMAIL"]
    password = os.environ["POCKETBASE_SUPERUSER_PASSWORD"]
    resp = requests.post(
        f"{PB_BASE_URL}/api/collections/_superusers/auth-with-password",
        json={"identity": email, "password": password},
        timeout=30,
    )
    assert resp.status_code == 200, (
        "Failed to authenticate as PocketBase superuser; status="
        f"{resp.status_code} body={resp.text!r}."
    )
    token = resp.json().get("token")
    assert token, f"Superuser auth response missing 'token': {resp.text!r}."
    return token


def test_users_collection_exists():
    token = _superuser_token()
    resp = requests.get(
        f"{PB_BASE_URL}/api/collections/users",
        headers={"Authorization": token},
        timeout=30,
    )
    assert resp.status_code == 200, (
        "Expected the `users` collection to exist before the task starts; "
        f"got status {resp.status_code}, body={resp.text!r}."
    )
    data = resp.json()
    assert data.get("name") == "users", (
        f"Collection metadata does not match name='users': {data!r}."
    )
    assert data.get("type") == "auth", (
        f"Expected `users` collection to be of type 'auth'; got: {data!r}."
    )


def test_posts_collection_exists():
    token = _superuser_token()
    resp = requests.get(
        f"{PB_BASE_URL}/api/collections/posts",
        headers={"Authorization": token},
        timeout=30,
    )
    assert resp.status_code == 200, (
        "Expected the `posts` collection to exist before the task starts; "
        f"got status {resp.status_code}, body={resp.text!r}."
    )
    data = resp.json()
    assert data.get("name") == "posts", (
        f"Collection metadata does not match name='posts': {data!r}."
    )
    assert data.get("type") == "base", (
        f"Expected `posts` collection to be of type 'base'; got: {data!r}."
    )


def test_user_post_stats_view_not_yet_present():
    token = _superuser_token()
    resp = requests.get(
        f"{PB_BASE_URL}/api/collections/user_post_stats",
        headers={"Authorization": token},
        timeout=30,
    )
    assert resp.status_code == 404, (
        "The `user_post_stats` view must NOT exist in the initial state; "
        f"got status {resp.status_code}, body={resp.text!r}."
    )
