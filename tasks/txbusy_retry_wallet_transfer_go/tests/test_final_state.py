import os
import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
import requests
from xprocess import ProcessStarter

PROJECT_DIR = "/home/user/myproject"
APP_BIN = os.path.join(PROJECT_DIR, "myapp")
PB_DATA = os.path.join(PROJECT_DIR, "pb_data")
HOST = "127.0.0.1"
PORT = 8090
BASE_URL = f"http://{HOST}:{PORT}"

TEST_USER_EMAIL = "tester@example.com"
TEST_USER_PASSWORD = "password12345"
SUPERUSER_EMAIL = "admin@example.com"
SUPERUSER_PASSWORD = "admin12345"


def _port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


@pytest.fixture(scope="session")
def server(xprocess):
    class Starter(ProcessStarter):
        name = "pocketbase_app"
        args = [APP_BIN, "serve", f"--http={HOST}:{PORT}", f"--dir={PB_DATA}"]
        env = os.environ.copy()
        popen_kwargs = {
            "cwd": PROJECT_DIR,
            "text": True,
        }
        timeout = 60
        terminate_on_interrupt = True

        def startup_check(self):
            if not _port_open(HOST, PORT):
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


def _superuser_token() -> str:
    r = requests.post(
        f"{BASE_URL}/api/collections/_superusers/auth-with-password",
        json={"identity": SUPERUSER_EMAIL, "password": SUPERUSER_PASSWORD},
        timeout=10,
    )
    assert r.status_code == 200, (
        f"Failed to authenticate as superuser: {r.status_code} {r.text}"
    )
    return r.json()["token"]


def _user_token() -> str:
    r = requests.post(
        f"{BASE_URL}/api/collections/users/auth-with-password",
        json={"identity": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
        timeout=10,
    )
    assert r.status_code == 200, (
        f"Failed to authenticate as tester user: {r.status_code} {r.text}"
    )
    return r.json()["token"]


def _list_wallets(super_token: str):
    r = requests.get(
        f"{BASE_URL}/api/collections/wallets/records",
        params={"perPage": 200, "sort": "balance"},
        headers={"Authorization": super_token},
        timeout=10,
    )
    assert r.status_code == 200, f"Failed to list wallets: {r.status_code} {r.text}"
    return r.json()["items"]


def _wallet_ids(super_token: str):
    items = _list_wallets(super_token)
    assert len(items) >= 2, f"Expected at least two wallets, got {items}."
    by_balance = {round(float(it["balance"])): it["id"] for it in items}
    # find one wallet with the highest balance => A, lowest => B
    sorted_items = sorted(items, key=lambda it: float(it["balance"]))
    id_b = sorted_items[0]["id"]
    id_a = sorted_items[-1]["id"]
    assert id_a != id_b, "Wallet A and wallet B must be distinct."
    return id_a, id_b


def _set_balance(super_token: str, wallet_id: str, balance: float):
    r = requests.patch(
        f"{BASE_URL}/api/collections/wallets/records/{wallet_id}",
        json={"balance": balance},
        headers={"Authorization": super_token},
        timeout=10,
    )
    assert r.status_code == 200, (
        f"Failed to reset wallet {wallet_id} balance: {r.status_code} {r.text}"
    )


def _get_balance(super_token: str, wallet_id: str) -> float:
    r = requests.get(
        f"{BASE_URL}/api/collections/wallets/records/{wallet_id}",
        headers={"Authorization": super_token},
        timeout=10,
    )
    assert r.status_code == 200, (
        f"Failed to fetch wallet {wallet_id}: {r.status_code} {r.text}"
    )
    return float(r.json()["balance"])


def _clear_transfers(super_token: str):
    page = 1
    while True:
        r = requests.get(
            f"{BASE_URL}/api/collections/transfers/records",
            params={"perPage": 200, "page": page},
            headers={"Authorization": super_token},
            timeout=10,
        )
        assert r.status_code == 200, (
            f"Failed to list transfers: {r.status_code} {r.text}"
        )
        data = r.json()
        for it in data["items"]:
            dr = requests.delete(
                f"{BASE_URL}/api/collections/transfers/records/{it['id']}",
                headers={"Authorization": super_token},
                timeout=10,
            )
            assert dr.status_code in (200, 204), (
                f"Failed to delete transfer {it['id']}: {dr.status_code} {dr.text}"
            )
        if page * data["perPage"] >= data["totalItems"]:
            break
        page += 1


def _transfers_count(super_token: str) -> int:
    r = requests.get(
        f"{BASE_URL}/api/collections/transfers/records",
        params={"perPage": 1},
        headers={"Authorization": super_token},
        timeout=10,
    )
    assert r.status_code == 200, (
        f"Failed to count transfers: {r.status_code} {r.text}"
    )
    return int(r.json()["totalItems"])


def _reset_state(super_token: str, id_a: str, id_b: str):
    _clear_transfers(super_token)
    _set_balance(super_token, id_a, 100)
    _set_balance(super_token, id_b, 0)


def test_single_transfer_succeeds(server):
    super_token = _superuser_token()
    id_a, id_b = _wallet_ids(super_token)
    _reset_state(super_token, id_a, id_b)

    user_token = _user_token()
    r = requests.post(
        f"{BASE_URL}/api/wallets/transfer",
        json={"fromId": id_a, "toId": id_b, "amount": 10},
        headers={"Authorization": user_token},
        timeout=10,
    )
    assert r.status_code == 200, (
        f"Expected HTTP 200 for a valid transfer, got {r.status_code}: {r.text}"
    )
    body = r.json()
    assert float(body.get("fromBalance", -1)) == 90, (
        f"Expected fromBalance=90 in response, got {body}."
    )
    assert float(body.get("toBalance", -1)) == 10, (
        f"Expected toBalance=10 in response, got {body}."
    )

    assert _get_balance(super_token, id_a) == 90, (
        "Wallet A balance was not persisted to 90 after single transfer."
    )
    assert _get_balance(super_token, id_b) == 10, (
        "Wallet B balance was not persisted to 10 after single transfer."
    )


def test_unauthenticated_transfer_is_rejected(server):
    super_token = _superuser_token()
    id_a, id_b = _wallet_ids(super_token)

    r = requests.post(
        f"{BASE_URL}/api/wallets/transfer",
        json={"fromId": id_a, "toId": id_b, "amount": 1},
        timeout=10,
    )
    assert r.status_code in (401, 403), (
        f"Expected 401/403 for unauthenticated transfer, got {r.status_code}: {r.text}"
    )


def test_50_concurrent_transfers_complete_without_deadlock(server):
    super_token = _superuser_token()
    id_a, id_b = _wallet_ids(super_token)
    _reset_state(super_token, id_a, id_b)

    user_token = _user_token()

    def do_transfer():
        return requests.post(
            f"{BASE_URL}/api/wallets/transfer",
            json={"fromId": id_a, "toId": id_b, "amount": 1},
            headers={"Authorization": user_token},
            timeout=30,
        )

    start = time.monotonic()
    statuses = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(do_transfer) for _ in range(50)]
        for fut in as_completed(futures):
            statuses.append(fut.result().status_code)
    elapsed = time.monotonic() - start

    assert elapsed < 30, (
        f"50 concurrent transfers must finish under 30s, took {elapsed:.2f}s."
    )
    assert all(s == 200 for s in statuses), (
        f"Expected every concurrent transfer to return HTTP 200, got statuses: {sorted(statuses)}."
    )

    assert _get_balance(super_token, id_a) == 50, (
        f"After 50x $1 concurrent transfers, A.balance must be 50, got {_get_balance(super_token, id_a)}."
    )
    assert _get_balance(super_token, id_b) == 50, (
        f"After 50x $1 concurrent transfers, B.balance must be 50, got {_get_balance(super_token, id_b)}."
    )
    assert _transfers_count(super_token) == 50, (
        f"Expected exactly 50 audit rows in transfers, got {_transfers_count(super_token)}."
    )


def test_insufficient_funds_returns_400_without_state_change(server):
    super_token = _superuser_token()
    id_a, id_b = _wallet_ids(super_token)
    _reset_state(super_token, id_a, id_b)

    user_token = _user_token()

    before_transfers = _transfers_count(super_token)
    r = requests.post(
        f"{BASE_URL}/api/wallets/transfer",
        json={"fromId": id_a, "toId": id_b, "amount": 9999},
        headers={"Authorization": user_token},
        timeout=10,
    )
    assert r.status_code == 400, (
        f"Expected HTTP 400 for insufficient funds, got {r.status_code}: {r.text}"
    )

    assert _get_balance(super_token, id_a) == 100, (
        "Wallet A balance should remain 100 after a failed transfer."
    )
    assert _get_balance(super_token, id_b) == 0, (
        "Wallet B balance should remain 0 after a failed transfer."
    )
    assert _transfers_count(super_token) == before_transfers, (
        "No new audit row should be inserted when the transfer fails."
    )
