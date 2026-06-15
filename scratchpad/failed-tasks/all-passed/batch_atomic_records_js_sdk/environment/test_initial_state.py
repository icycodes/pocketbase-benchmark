import os
import shutil
import subprocess
import time

import pytest
import requests

PROJECT_DIR = "/home/user/myproject"
PB_URL = os.environ.get("PB_URL", "http://127.0.0.1:8090")
PB_ADMIN_EMAIL = os.environ.get("PB_ADMIN_EMAIL", "admin@example.com")
PB_ADMIN_PASSWORD = os.environ.get("PB_ADMIN_PASSWORD", "Adminpass12345!")


@pytest.fixture(autouse=True, scope="session")
def _start_pocketbase_server():
    """Ensure the embedded PocketBase server is running for the test session."""
    subprocess.run(
        ["/usr/local/bin/start-pocketbase.sh"],
        check=True,
        capture_output=True,
        text=True,
    )
    yield


def _wait_for_server(timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    last_err = None
    while time.time() < deadline:
        try:
            r = requests.get(f"{PB_URL}/api/health", timeout=2)
            if r.status_code == 200:
                return
        except Exception as e:  # noqa: BLE001
            last_err = e
        time.sleep(0.5)
    raise AssertionError(
        f"PocketBase server at {PB_URL} did not become healthy in time: {last_err}"
    )


def _superuser_token() -> str:
    _wait_for_server()
    r = requests.post(
        f"{PB_URL}/api/collections/_superusers/auth-with-password",
        json={"identity": PB_ADMIN_EMAIL, "password": PB_ADMIN_PASSWORD},
        timeout=10,
    )
    assert r.status_code == 200, (
        f"Superuser auth failed (status={r.status_code}): {r.text}"
    )
    return r.json()["token"]


def test_node_binary_available():
    assert shutil.which("node") is not None, "node binary not found in PATH."


def test_npm_binary_available():
    assert shutil.which("npm") is not None, "npm binary not found in PATH."


def test_pocketbase_binary_available():
    assert shutil.which("pocketbase") is not None, (
        "pocketbase binary not found in PATH."
    )


def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR), (
        f"Project directory {PROJECT_DIR} does not exist."
    )


def test_pocketbase_sdk_installed():
    # The pocketbase npm package must be pre-installed so the executor can use it.
    sdk_pkg_json = os.path.join(
        PROJECT_DIR, "node_modules", "pocketbase", "package.json"
    )
    assert os.path.isfile(sdk_pkg_json), (
        f"PocketBase JS SDK is not installed at {sdk_pkg_json}."
    )


def test_pocketbase_server_healthy():
    _wait_for_server()
    r = requests.get(f"{PB_URL}/api/health", timeout=5)
    assert r.status_code == 200, (
        f"PocketBase /api/health returned status {r.status_code}: {r.text}"
    )


def test_batch_api_enabled_in_settings():
    token = _superuser_token()
    r = requests.get(
        f"{PB_URL}/api/settings",
        headers={"Authorization": token},
        timeout=10,
    )
    assert r.status_code == 200, (
        f"Could not read settings (status={r.status_code}): {r.text}"
    )
    settings = r.json()
    batch_cfg = settings.get("batch") or {}
    assert batch_cfg.get("enabled") is True, (
        "Batch Web API is not enabled in PocketBase settings."
    )
    assert int(batch_cfg.get("maxRequests", 0)) >= 50, (
        "Batch maxRequests must be high enough to accept >=50 sub-requests."
    )


def _get_collection(token: str, name: str) -> dict:
    r = requests.get(
        f"{PB_URL}/api/collections/{name}",
        headers={"Authorization": token},
        timeout=10,
    )
    assert r.status_code == 200, (
        f"Collection '{name}' not found (status={r.status_code}): {r.text}"
    )
    return r.json()


def test_orders_collection_exists():
    token = _superuser_token()
    col = _get_collection(token, "orders")
    field_names = {f["name"] for f in col.get("fields", [])}
    for required in ("customer", "total"):
        assert required in field_names, (
            f"orders collection is missing field '{required}'."
        )


def test_order_items_collection_exists():
    token = _superuser_token()
    col = _get_collection(token, "order_items")
    field_names = {f["name"] for f in col.get("fields", [])}
    for required in ("order", "product", "quantity"):
        assert required in field_names, (
            f"order_items collection is missing field '{required}'."
        )
    # The 'order' field must be a relation pointing at the orders collection.
    order_field = next(
        (f for f in col.get("fields", []) if f["name"] == "order"), None
    )
    assert order_field is not None, "order_items.order field is missing."
    assert order_field.get("type") == "relation", (
        "order_items.order must be a relation field."
    )


def test_collections_are_initially_empty():
    token = _superuser_token()
    for name in ("orders", "order_items"):
        r = requests.get(
            f"{PB_URL}/api/collections/{name}/records?perPage=1",
            headers={"Authorization": token},
            timeout=10,
        )
        assert r.status_code == 200, (
            f"Could not list records of {name}: {r.status_code} {r.text}"
        )
        assert r.json().get("totalItems", 0) == 0, (
            f"Collection {name} should be empty before the task starts."
        )


def test_required_env_vars_present():
    for var in ("ZEALT_RUN_ID", "PB_URL", "PB_ADMIN_EMAIL", "PB_ADMIN_PASSWORD"):
        assert os.environ.get(var), f"Required environment variable {var} is not set."
