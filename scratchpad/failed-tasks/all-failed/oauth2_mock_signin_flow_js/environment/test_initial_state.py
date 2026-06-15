import os
import shutil
import subprocess
import time

import pytest
import requests

PROJECT_DIR = "/home/user/myproject"
PB_URL = os.environ.get("PB_URL", "http://127.0.0.1:8090")
MOCK_OAUTH_URL = os.environ.get("MOCK_OAUTH_URL", "http://127.0.0.1:9000")
PB_SUPERUSER_EMAIL = os.environ.get("PB_SUPERUSER_EMAIL", "")
PB_SUPERUSER_PASSWORD = os.environ.get("PB_SUPERUSER_PASSWORD", "")


@pytest.fixture(scope="session", autouse=True)
def _start_services():
    # Idempotently boot PocketBase + the mock OAuth2 server. The script
    # detaches them via setsid so they persist beyond the pytest process.
    result = subprocess.run(
        ["/usr/local/bin/start_services.sh"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, (
        f"start_services.sh failed (exit {result.returncode}). "
        f"stderr:\n{result.stderr}\nstdout:\n{result.stdout}"
    )
    yield


def _wait_for(url: str, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    last_err = None
    while time.time() < deadline:
        try:
            r = requests.get(url, timeout=2)
            if r.status_code < 500:
                return True
        except Exception as e:  # noqa: BLE001
            last_err = e
        time.sleep(0.5)
    if last_err is not None:
        print(f"last error waiting for {url}: {last_err}")
    return False


def _superuser_token() -> str:
    resp = requests.post(
        f"{PB_URL}/api/collections/_superusers/auth-with-password",
        json={"identity": PB_SUPERUSER_EMAIL, "password": PB_SUPERUSER_PASSWORD},
        timeout=10,
    )
    assert resp.status_code == 200, (
        f"Failed to authenticate superuser at {PB_URL}: "
        f"{resp.status_code} {resp.text}"
    )
    token = resp.json().get("token")
    assert token, "Superuser auth response did not contain a token."
    return token


def test_node_binary_available():
    assert shutil.which("node") is not None, "node binary not found in PATH."


def test_pocketbase_binary_available():
    assert shutil.which("pocketbase") is not None, "pocketbase binary not found in PATH."


def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} does not exist."


def test_pocketbase_server_running():
    assert _wait_for(f"{PB_URL}/api/health"), (
        f"PocketBase server is not reachable at {PB_URL}/api/health"
    )


def test_mock_oauth_server_running():
    assert _wait_for(f"{MOCK_OAUTH_URL}/health"), (
        f"Mock OAuth2 server is not reachable at {MOCK_OAUTH_URL}/health"
    )


def test_mock_oauth_endpoints_respond():
    # The authorize endpoint should return a 302 redirect with a code.
    redirect_uri = "http://127.0.0.1:8090/api/oauth2-redirect"
    r = requests.get(
        f"{MOCK_OAUTH_URL}/authorize",
        params={
            "client_id": "mock-client-id",
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "state": "initstate",
        },
        allow_redirects=False,
        timeout=5,
    )
    assert r.status_code in (302, 303), (
        f"Mock OAuth /authorize should redirect, got {r.status_code}"
    )
    location = r.headers.get("Location", "")
    assert "code=" in location, f"Mock OAuth /authorize redirect missing code: {location}"


def test_users_collection_has_mockoauth_provider_configured():
    token = _superuser_token()
    resp = requests.get(
        f"{PB_URL}/api/collections/users",
        headers={"Authorization": token},
        timeout=10,
    )
    assert resp.status_code == 200, (
        f"Failed to fetch users collection: {resp.status_code} {resp.text}"
    )
    collection = resp.json()
    oauth2 = collection.get("oauth2") or {}
    assert oauth2.get("enabled") is True, (
        "users collection oauth2 should be enabled in the initial state."
    )
    providers = oauth2.get("providers") or []
    matching = [p for p in providers if p.get("displayName") == "mockoauth"]
    assert len(matching) >= 1, (
        f"users collection should have at least one provider with displayName 'mockoauth'. "
        f"Got providers: {providers}"
    )
    provider = matching[0]
    for key in ("authURL", "tokenURL", "userInfoURL"):
        url = provider.get(key, "")
        assert isinstance(url, str) and url.startswith(MOCK_OAUTH_URL), (
            f"Provider {key} should start with {MOCK_OAUTH_URL}, got {url!r}"
        )


def test_users_collection_has_no_records_yet():
    token = _superuser_token()
    resp = requests.get(
        f"{PB_URL}/api/collections/users/records",
        headers={"Authorization": token},
        params={"perPage": 1},
        timeout=10,
    )
    assert resp.status_code == 200, (
        f"Failed to list users: {resp.status_code} {resp.text}"
    )
    data = resp.json()
    items = data.get("items") or []
    for item in items:
        assert item.get("email") != "oauth-user@example.com", (
            "users collection should not yet contain oauth-user@example.com in initial state."
        )
