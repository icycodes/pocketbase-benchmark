import glob
import os
import socket

import pytest
import requests
from xprocess import ProcessStarter

PROJECT_DIR = "/home/user/myproject"
HOOKS_DIR = os.path.join(PROJECT_DIR, "pb_hooks")
POCKETBASE_BIN = os.path.join(PROJECT_DIR, "pocketbase")
BASE_URL = "http://127.0.0.1:8090"
PORT = 8090


@pytest.fixture(scope="session")
def start_pocketbase(xprocess):
    """Start the PocketBase server using the start command from the task.json truth."""

    class Starter(ProcessStarter):
        name = "pocketbase_server"
        args = [
            POCKETBASE_BIN,
            "serve",
            "--http=0.0.0.0:8090",
            "--dir=./pb_data",
            "--hooksDir=./pb_hooks",
            "--migrationsDir=./pb_migrations",
        ]
        env = os.environ.copy()
        popen_kwargs = {
            "cwd": PROJECT_DIR,
            "text": True,
        }
        timeout = 60
        terminate_on_interrupt = True

        def startup_check(self):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(("127.0.0.1", PORT)) != 0:
                    return False
            try:
                r = requests.get(f"{BASE_URL}/api/health", timeout=2)
                return r.status_code == 200
            except requests.RequestException:
                return False

    xprocess.ensure(Starter.name, Starter)

    yield

    info = xprocess.getinfo(Starter.name)
    info.terminate()


def test_pb_hooks_contains_pb_js_file():
    """A JSVM hook file must be present under pb_hooks/."""
    pattern = os.path.join(HOOKS_DIR, "*.pb.js")
    matches = glob.glob(pattern)
    assert matches, (
        f"Expected at least one '*.pb.js' file in {HOOKS_DIR}, but none was found."
    )


def test_health_endpoint_still_works(start_pocketbase):
    """The built-in PocketBase health endpoint must continue to respond."""
    response = requests.get(f"{BASE_URL}/api/health", timeout=10)
    assert response.status_code == 200, (
        f"Expected GET /api/health to return 200, got {response.status_code}: "
        f"{response.text}"
    )
    try:
        payload = response.json()
    except ValueError as exc:
        pytest.fail(f"GET /api/health did not return valid JSON: {exc}")
    assert payload.get("code") == 200, (
        f"Expected /api/health response to include 'code': 200, got: {payload}"
    )


def test_custom_route_returns_greeting_for_world(start_pocketbase):
    """GET /api/myapp/hello/world should return {'message': 'Hello, world!'}."""
    response = requests.get(f"{BASE_URL}/api/myapp/hello/world", timeout=10)
    assert response.status_code == 200, (
        f"Expected GET /api/myapp/hello/world to return 200, got "
        f"{response.status_code}: {response.text}"
    )
    try:
        payload = response.json()
    except ValueError as exc:
        pytest.fail(
            f"GET /api/myapp/hello/world did not return valid JSON: {exc}; "
            f"body: {response.text}"
        )
    assert payload == {"message": "Hello, world!"}, (
        f"Expected JSON body to be exactly {{'message': 'Hello, world!'}}, "
        f"got: {payload}"
    )


def test_custom_route_reflects_path_parameter(start_pocketbase):
    """The {name} path parameter must be reflected exactly in the JSON response."""
    cases = {
        "PocketBase": {"message": "Hello, PocketBase!"},
        "Alice": {"message": "Hello, Alice!"},
    }
    for name, expected in cases.items():
        response = requests.get(f"{BASE_URL}/api/myapp/hello/{name}", timeout=10)
        assert response.status_code == 200, (
            f"Expected GET /api/myapp/hello/{name} to return 200, got "
            f"{response.status_code}: {response.text}"
        )
        try:
            payload = response.json()
        except ValueError as exc:
            pytest.fail(
                f"GET /api/myapp/hello/{name} did not return valid JSON: {exc}; "
                f"body: {response.text}"
            )
        assert payload == expected, (
            f"Expected JSON body for /api/myapp/hello/{name} to be {expected}, "
            f"got: {payload}"
        )


def test_custom_route_accessible_without_auth(start_pocketbase):
    """The endpoint must be reachable by guests (no Authorization header)."""
    # Force a fresh session without any default auth headers.
    session = requests.Session()
    session.headers.pop("Authorization", None)
    response = session.get(f"{BASE_URL}/api/myapp/hello/world", timeout=10)
    assert response.status_code == 200, (
        f"Expected guest GET /api/myapp/hello/world to return 200, got "
        f"{response.status_code}: {response.text}"
    )
