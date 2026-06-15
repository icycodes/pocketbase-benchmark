import io
import os
import shutil
import socket
import subprocess
import time

import pytest
import requests
from xprocess import ProcessStarter


PROJECT_DIR = "/home/user/myproject"
PB_SEED_DIR = "/opt/pb_seed"
PB_URL = "http://127.0.0.1:8090"
IMPORT_URL = f"{PB_URL}/api/import/products"
SUPER_AUTH_URL = f"{PB_URL}/api/collections/_superusers/auth-with-password"
USER_AUTH_URL = f"{PB_URL}/api/collections/users/auth-with-password"
USERS_RECORDS_URL = f"{PB_URL}/api/collections/users/records"
PRODUCTS_RECORDS_URL = f"{PB_URL}/api/collections/products/records"
HEALTH_URL = f"{PB_URL}/api/health"

REGULAR_EMAIL = "regular@example.com"
REGULAR_PASSWORD = "regular-pass-12345"


def _build_binary_if_missing():
    binary = os.path.join(PROJECT_DIR, "myapp")
    if not os.path.isfile(binary):
        result = subprocess.run(
            ["go", "build", "-o", "myapp", "."],
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, (
            f"Failed to build the Go binary: stdout={result.stdout!r}, "
            f"stderr={result.stderr!r}"
        )


def _seed_pb_data_if_missing():
    target = os.path.join(PROJECT_DIR, "pb_data")
    src = os.path.join(PB_SEED_DIR, "pb_data")
    if not os.path.isfile(os.path.join(target, "data.db")):
        os.makedirs(target, exist_ok=True)
        # Copy contents from seeded dir into target dir.
        for name in os.listdir(src):
            s = os.path.join(src, name)
            d = os.path.join(target, name)
            if os.path.isdir(s):
                if os.path.exists(d):
                    shutil.rmtree(d)
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)


def _port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


@pytest.fixture(scope="session")
def pb_server(xprocess):
    _seed_pb_data_if_missing()
    _build_binary_if_missing()

    class Starter(ProcessStarter):
        name = "pb_server"
        args = [os.path.join(PROJECT_DIR, "myapp"), "serve", "--http=0.0.0.0:8090"]
        env = os.environ.copy()
        popen_kwargs = {
            "cwd": PROJECT_DIR,
            "text": True,
        }
        timeout = 120
        terminate_on_interrupt = True

        def startup_check(self):
            if not _port_open("127.0.0.1", 8090):
                return False
            try:
                r = requests.get(HEALTH_URL, timeout=2)
                return r.status_code == 200
            except requests.RequestException:
                return False

    xprocess.ensure(Starter.name, Starter)
    yield
    info = xprocess.getinfo(Starter.name)
    info.terminate()


@pytest.fixture(scope="session")
def super_token(pb_server):
    email = os.environ.get("PB_SUPERUSER_EMAIL")
    password = os.environ.get("PB_SUPERUSER_PASSWORD")
    assert email and password, (
        "PB_SUPERUSER_EMAIL / PB_SUPERUSER_PASSWORD env vars must be set."
    )
    r = requests.post(
        SUPER_AUTH_URL,
        json={"identity": email, "password": password},
        timeout=10,
    )
    assert r.status_code == 200, (
        f"Superuser auth failed: status={r.status_code}, body={r.text!r}"
    )
    token = r.json().get("token")
    assert token, f"Superuser auth response missing token: {r.text!r}"
    return token


def _clear_products(super_token: str):
    """Delete every record in the products collection."""
    headers = {"Authorization": f"Bearer {super_token}"}
    # Fetch all records (perPage=500 should be plenty for our small tests).
    r = requests.get(
        f"{PRODUCTS_RECORDS_URL}?perPage=500",
        headers=headers,
        timeout=10,
    )
    assert r.status_code == 200, (
        f"Listing products failed: status={r.status_code}, body={r.text!r}. "
        "The products collection may not have been created."
    )
    for item in r.json().get("items", []):
        rid = item["id"]
        d = requests.delete(
            f"{PRODUCTS_RECORDS_URL}/{rid}",
            headers=headers,
            timeout=10,
        )
        assert d.status_code in (200, 204), (
            f"Failed to delete product {rid}: status={d.status_code}, body={d.text!r}"
        )


def _list_products(super_token: str):
    headers = {"Authorization": f"Bearer {super_token}"}
    r = requests.get(
        f"{PRODUCTS_RECORDS_URL}?perPage=500",
        headers=headers,
        timeout=10,
    )
    assert r.status_code == 200, (
        f"Listing products failed: status={r.status_code}, body={r.text!r}"
    )
    return r.json().get("items", [])


@pytest.fixture(scope="session")
def user_token(super_token):
    headers = {"Authorization": f"Bearer {super_token}"}
    # Create user (idempotent: if it already exists we just authenticate).
    create = requests.post(
        USERS_RECORDS_URL,
        headers=headers,
        json={
            "email": REGULAR_EMAIL,
            "password": REGULAR_PASSWORD,
            "passwordConfirm": REGULAR_PASSWORD,
            "emailVisibility": True,
        },
        timeout=10,
    )
    # 200 created OR 400 if user already exists - both are acceptable.
    assert create.status_code in (200, 400), (
        f"Unexpected status while creating regular user: {create.status_code}, "
        f"body={create.text!r}"
    )
    auth = requests.post(
        USER_AUTH_URL,
        json={"identity": REGULAR_EMAIL, "password": REGULAR_PASSWORD},
        timeout=10,
    )
    assert auth.status_code == 200, (
        f"Regular user auth failed: status={auth.status_code}, body={auth.text!r}"
    )
    token = auth.json().get("token")
    assert token, f"Regular user auth response missing token: {auth.text!r}"
    return token


VALID_CSV_10 = (
    "sku,name,price\n"
    "SKU-001,Widget A,10\n"
    "SKU-002,Widget B,12.5\n"
    "SKU-003,Widget C,1\n"
    "SKU-004,Widget D,99.99\n"
    "SKU-005,Widget E,7\n"
    "SKU-006,Widget F,15\n"
    "SKU-007,Widget G,2.5\n"
    "SKU-008,Widget H,42\n"
    "SKU-009,Widget I,3.14\n"
    "SKU-010,Widget J,21\n"
)

INVALID_PRICE_CSV = (
    "sku,name,price\n"
    "SKU-100,Good Widget,10\n"
    "SKU-101,Bad Widget,0\n"
    "SKU-102,Another Good Widget,5\n"
)

DUPLICATE_SKU_CSV = (
    "sku,name,price\n"
    "SKU-200,One,5\n"
    "SKU-201,Two,5\n"
    "SKU-200,Three,5\n"
)


def _post_csv(csv_body: str, token: str | None):
    files = {"file": ("data.csv", io.BytesIO(csv_body.encode("utf-8")), "text/csv")}
    headers = {}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    return requests.post(IMPORT_URL, headers=headers, files=files, timeout=30)


def test_valid_batch_import_returns_200_and_inserts_all_rows(super_token):
    _clear_products(super_token)
    r = _post_csv(VALID_CSV_10, super_token)
    assert r.status_code == 200, (
        f"Expected 200 for valid CSV, got {r.status_code}: {r.text!r}"
    )
    body = r.json()
    assert body.get("inserted") == 10, (
        f"Expected inserted=10, got {body!r}"
    )
    assert body.get("errors") == [], (
        f"Expected empty errors array, got {body!r}"
    )

    items = _list_products(super_token)
    assert len(items) == 10, (
        f"Expected 10 records in products, found {len(items)}: {items!r}"
    )
    skus = {it.get("sku") for it in items}
    expected_skus = {f"SKU-{n:03d}" for n in range(1, 11)}
    assert skus == expected_skus, (
        f"Expected SKUs {expected_skus}, got {skus}"
    )


def test_invalid_price_rolls_back_entire_batch(super_token):
    _clear_products(super_token)
    r = _post_csv(INVALID_PRICE_CSV, super_token)
    assert r.status_code == 400, (
        f"Expected 400 for CSV with invalid price, got {r.status_code}: {r.text!r}"
    )
    body = r.json()
    assert body.get("inserted") == 0, (
        f"Expected inserted=0 for a failing batch, got {body!r}"
    )
    errors = body.get("errors")
    assert isinstance(errors, list) and len(errors) >= 1, (
        f"Expected non-empty errors array, got {body!r}"
    )
    # The offending row is row 2 (1-based, excluding header) -> SKU-101.
    rows = [e.get("row") for e in errors if isinstance(e, dict)]
    assert 2 in rows, (
        f"Expected an error entry with row=2, got rows={rows} (full body={body!r})"
    )
    matching = [e for e in errors if isinstance(e, dict) and e.get("row") == 2]
    assert matching, f"No error entry for row=2 found in {errors!r}"
    reason = matching[0].get("reason")
    assert isinstance(reason, str) and reason.strip(), (
        f"Expected non-empty 'reason' string in error entry, got {matching[0]!r}"
    )
    assert "price" in reason.lower(), (
        f"Expected error reason to mention 'price', got: {reason!r}"
    )

    items = _list_products(super_token)
    assert len(items) == 0, (
        f"Expected rollback (0 records), but found {len(items)}: {items!r}"
    )


def test_duplicate_sku_within_file_rolls_back(super_token):
    _clear_products(super_token)
    r = _post_csv(DUPLICATE_SKU_CSV, super_token)
    assert r.status_code == 400, (
        f"Expected 400 for CSV with duplicate sku, got {r.status_code}: {r.text!r}"
    )
    body = r.json()
    assert body.get("inserted") == 0, (
        f"Expected inserted=0 for a failing batch, got {body!r}"
    )
    errors = body.get("errors")
    assert isinstance(errors, list) and len(errors) >= 1, (
        f"Expected non-empty errors array, got {body!r}"
    )
    items = _list_products(super_token)
    assert len(items) == 0, (
        f"Expected rollback (0 records), but found {len(items)}: {items!r}"
    )


def test_unauthenticated_request_returns_401(super_token):
    _clear_products(super_token)
    r = _post_csv(VALID_CSV_10, token=None)
    assert r.status_code == 401, (
        f"Expected 401 for unauthenticated request, got {r.status_code}: {r.text!r}"
    )
    items = _list_products(super_token)
    assert len(items) == 0, (
        f"Expected zero records after 401 response, found {len(items)}: {items!r}"
    )


def test_non_superuser_request_returns_403(super_token, user_token):
    _clear_products(super_token)
    r = _post_csv(VALID_CSV_10, user_token)
    assert r.status_code == 403, (
        f"Expected 403 for regular-user request, got {r.status_code}: {r.text!r}"
    )
    items = _list_products(super_token)
    assert len(items) == 0, (
        f"Expected zero records after 403 response, found {len(items)}: {items!r}"
    )


def test_rerun_after_failed_batch_still_succeeds(super_token):
    _clear_products(super_token)
    # First trigger a failure to make sure the previous transaction is fully rolled back.
    failure = _post_csv(INVALID_PRICE_CSV, super_token)
    assert failure.status_code == 400, (
        f"Expected 400 from priming failure call, got {failure.status_code}: "
        f"{failure.text!r}"
    )
    assert len(_list_products(super_token)) == 0, (
        "Failed batch left rows in the database; transaction did not roll back."
    )

    # Now submit a valid batch and ensure it fully succeeds.
    success = _post_csv(VALID_CSV_10, super_token)
    assert success.status_code == 200, (
        f"Expected 200 after rollback, got {success.status_code}: {success.text!r}"
    )
    body = success.json()
    assert body.get("inserted") == 10, (
        f"Expected inserted=10 on re-run, got {body!r}"
    )
    assert body.get("errors") == [], (
        f"Expected empty errors on re-run, got {body!r}"
    )

    items = _list_products(super_token)
    assert len(items) == 10, (
        f"Expected 10 records after re-run, found {len(items)}: {items!r}"
    )
    skus = {it.get("sku") for it in items}
    expected_skus = {f"SKU-{n:03d}" for n in range(1, 11)}
    assert skus == expected_skus, (
        f"Expected SKUs {expected_skus} after re-run, got {skus}"
    )
