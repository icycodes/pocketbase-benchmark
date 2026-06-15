import os
import re
import subprocess
import time

import pytest
import requests


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

PROJECT_DIR = "/home/user/myproject"
PB_URL = os.environ.get("PB_URL", "http://127.0.0.1:8090")
PB_ADMIN_EMAIL = os.environ.get("PB_ADMIN_EMAIL", "admin@example.com")
PB_ADMIN_PASSWORD = os.environ.get("PB_ADMIN_PASSWORD", "Adminpass12345!")
ZEALT_RUN_ID = os.environ.get("ZEALT_RUN_ID", "")

APP_FILE = os.path.join(PROJECT_DIR, "app.js")
ORDER_ID_RE = re.compile(r"^ORDER:([a-z0-9]{15})$")


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


def _count_orders_for_run(token: str) -> int:
    assert ZEALT_RUN_ID, "ZEALT_RUN_ID must be set for verification."
    filt = f'customer = "{ZEALT_RUN_ID}"'
    r = requests.get(
        f"{PB_URL}/api/collections/orders/records",
        headers={"Authorization": token},
        params={"filter": filt, "perPage": 1},
        timeout=10,
    )
    assert r.status_code == 200, (
        f"Could not list orders (status={r.status_code}): {r.text}"
    )
    return int(r.json().get("totalItems", 0))


def _count_total_items(token: str) -> int:
    r = requests.get(
        f"{PB_URL}/api/collections/order_items/records",
        headers={"Authorization": token},
        params={"perPage": 1},
        timeout=10,
    )
    assert r.status_code == 200, (
        f"Could not list order_items (status={r.status_code}): {r.text}"
    )
    return int(r.json().get("totalItems", 0))


def _run_node(args, timeout: float = 60.0) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    return subprocess.run(
        ["node", APP_FILE, *args],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )


def test_app_file_exists():
    assert os.path.isfile(APP_FILE), f"app.js script not found at {APP_FILE}."


def test_fail_case_rolls_back_batch():
    """Run the --fail case FIRST so we can detect rollback correctness reliably."""
    token = _superuser_token()
    orders_before = _count_orders_for_run(token)
    items_before = _count_total_items(token)

    result = _run_node(["--items", "3", "--fail"])

    assert result.returncode == 1, (
        "Expected exit code 1 for --fail, got "
        f"{result.returncode}. stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "BATCH_ROLLED_BACK" in result.stderr, (
        "Expected the literal token 'BATCH_ROLLED_BACK' in stderr for --fail run. "
        f"stderr={result.stderr!r}"
    )

    # Re-auth in case token aged out; use a fresh token for state assertions.
    token = _superuser_token()
    orders_after = _count_orders_for_run(token)
    items_after = _count_total_items(token)
    assert orders_after == orders_before, (
        "Failed batch must roll back: orders count for this run-id changed from "
        f"{orders_before} to {orders_after}."
    )
    assert items_after == items_before, (
        "Failed batch must roll back: total order_items count changed from "
        f"{items_before} to {items_after}."
    )


def test_happy_path_creates_order_and_three_items():
    result = _run_node(["--items", "3"])
    assert result.returncode == 0, (
        "Expected exit code 0 for happy path, got "
        f"{result.returncode}. stdout={result.stdout!r} stderr={result.stderr!r}"
    )

    stdout = result.stdout.strip().splitlines()
    assert stdout, f"stdout is empty. stderr={result.stderr!r}"
    last_line = stdout[-1].strip()
    m = ORDER_ID_RE.match(last_line)
    assert m, (
        "stdout must contain a line matching ^ORDER:[a-z0-9]{15}$ . "
        f"Got: {last_line!r}"
    )
    order_id = m.group(1)

    token = _superuser_token()

    # Verify the order itself.
    r = requests.get(
        f"{PB_URL}/api/collections/orders/records/{order_id}",
        headers={"Authorization": token},
        timeout=10,
    )
    assert r.status_code == 200, (
        f"Created order {order_id} not found via REST (status={r.status_code}): {r.text}"
    )
    order = r.json()
    assert order.get("customer") == ZEALT_RUN_ID, (
        "Order customer field must equal $ZEALT_RUN_ID. "
        f"Got customer={order.get('customer')!r}, expected {ZEALT_RUN_ID!r}."
    )

    # Verify exactly 3 items linked to this order.
    r = requests.get(
        f"{PB_URL}/api/collections/order_items/records",
        headers={"Authorization": token},
        params={"filter": f'order = "{order_id}"', "perPage": 200},
        timeout=10,
    )
    assert r.status_code == 200, (
        f"Could not list order_items for order {order_id}: {r.status_code} {r.text}"
    )
    items_payload = r.json()
    items = items_payload.get("items", [])
    assert items_payload.get("totalItems") == 3 and len(items) == 3, (
        f"Expected exactly 3 order_items referencing order {order_id}, got "
        f"{items_payload.get('totalItems')} (page items: {len(items)})."
    )
    for it in items:
        assert it.get("order") == order_id, (
            f"order_items.order should reference {order_id}, got {it.get('order')!r}."
        )
        assert isinstance(it.get("quantity"), (int, float)) and it["quantity"] >= 1, (
            f"order_items.quantity must be >= 1, got {it.get('quantity')!r}."
        )
        assert isinstance(it.get("product"), str) and it["product"], (
            f"order_items.product must be a non-empty string, got {it.get('product')!r}."
        )


def test_script_uses_batch_interface():
    """The script must use the SDK batch interface, not a per-record loop."""
    with open(APP_FILE, "r", encoding="utf-8") as f:
        source = f.read()
    assert "createBatch" in source, (
        "app.js must call pb.createBatch() to construct a batch transaction."
    )
    assert re.search(r"\.send\s*\(", source), (
        "app.js must call batch.send() to dispatch the batch as one request."
    )
