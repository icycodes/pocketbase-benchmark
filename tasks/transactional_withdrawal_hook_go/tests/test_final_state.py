import os
import socket
import time

import pytest
import requests
from xprocess import ProcessStarter

PROJECT_DIR = "/home/user/myproject"
BASE_URL = "http://127.0.0.1:8090"


def _run_id() -> str:
    return os.environ.get("ZEALT_RUN_ID", "local")


def _port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        return s.connect_ex((host, port)) == 0


def _wait_for_health(timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    last_err: str = ""
    while time.time() < deadline:
        try:
            r = requests.get(f"{BASE_URL}/api/health", timeout=2)
            if r.status_code == 200:
                return
            last_err = f"status={r.status_code}"
        except Exception as e:  # noqa: BLE001
            last_err = str(e)
        time.sleep(0.5)
    raise RuntimeError(f"PocketBase did not become healthy in {timeout}s: {last_err}")


@pytest.fixture(scope="session")
def start_app(xprocess):
    """Start the compiled wallet-app binary if it is not already serving on port 8090."""

    if _port_open("127.0.0.1", 8090):
        # Server already started by the executor; just wait for health.
        _wait_for_health()
        yield
        return

    class Starter(ProcessStarter):
        name = "wallet_app"
        args = ["./wallet-app", "serve", "--http=0.0.0.0:8090"]
        env = os.environ.copy()
        popen_kwargs = {
            "cwd": PROJECT_DIR,
            "text": True,
        }
        timeout = 60
        terminate_on_interrupt = True

        def startup_check(self):
            try:
                r = requests.get(f"{BASE_URL}/api/health", timeout=1)
                return r.status_code == 200
            except Exception:  # noqa: BLE001
                return False

    xprocess.ensure(Starter.name, Starter)

    yield

    info = xprocess.getinfo(Starter.name)
    info.terminate()


def _create_wallet(owner: str, balance: float) -> dict:
    r = requests.post(
        f"{BASE_URL}/api/collections/wallets/records",
        json={"owner": owner, "balance": balance},
        timeout=10,
    )
    assert r.status_code in (200, 201), (
        f"Seeding wallet '{owner}' failed: status={r.status_code}, body={r.text}"
    )
    data = r.json()
    assert data.get("id"), f"Seeded wallet response is missing 'id': {data}"
    return data


def _get_wallet(wallet_id: str) -> dict:
    r = requests.get(f"{BASE_URL}/api/collections/wallets/records/{wallet_id}", timeout=10)
    assert r.status_code == 200, (
        f"GET wallet {wallet_id} failed: status={r.status_code}, body={r.text}"
    )
    return r.json()


def _post_withdrawal(wallet_id: str, amount: float, note: str) -> requests.Response:
    return requests.post(
        f"{BASE_URL}/api/collections/withdrawals/records",
        json={"wallet": wallet_id, "amount": amount, "note": note},
        timeout=10,
    )


def _count_withdrawals_by_note(note: str) -> int:
    r = requests.get(
        f"{BASE_URL}/api/collections/withdrawals/records",
        params={"filter": f'(note="{note}")', "perPage": 50},
        timeout=10,
    )
    assert r.status_code == 200, (
        f"List withdrawals (note={note}) failed: status={r.status_code}, body={r.text}"
    )
    return int(r.json().get("totalItems", 0))


def test_happy_path_debits_and_persists(start_app):
    run_id = _run_id()
    wallet = _create_wallet(f"wallet-happy-{run_id}", 100)
    wallet_id = wallet["id"]

    note = f"happy-{run_id}"
    r = _post_withdrawal(wallet_id, 30, note)
    assert r.status_code == 200, (
        f"Expected HTTP 200 for valid withdrawal, got {r.status_code}: {r.text}"
    )
    body = r.json()
    assert body.get("wallet") == wallet_id, (
        f"Expected withdrawal.wallet=={wallet_id}, got {body.get('wallet')}"
    )
    assert float(body.get("amount", 0)) == 30, (
        f"Expected withdrawal.amount==30, got {body.get('amount')}"
    )
    assert body.get("note") == note, (
        f"Expected withdrawal.note=={note!r}, got {body.get('note')!r}"
    )
    withdrawal_id = body.get("id")
    assert withdrawal_id, f"Expected non-empty withdrawal id, got: {body}"

    after = _get_wallet(wallet_id)
    assert float(after.get("balance", -1)) == 70, (
        f"Expected wallet balance to drop to 70, got {after.get('balance')}"
    )

    fetched = requests.get(
        f"{BASE_URL}/api/collections/withdrawals/records/{withdrawal_id}", timeout=10
    )
    assert fetched.status_code == 200, (
        f"Expected created withdrawal to be retrievable, got {fetched.status_code}: {fetched.text}"
    )
    fetched_body = fetched.json()
    assert fetched_body.get("id") == withdrawal_id, (
        f"Retrieved withdrawal id mismatch: {fetched_body}"
    )
    assert float(fetched_body.get("amount", 0)) == 30, (
        f"Retrieved withdrawal amount mismatch: {fetched_body}"
    )


def test_sequential_withdrawals_chain(start_app):
    run_id = _run_id()
    wallet = _create_wallet(f"wallet-seq-{run_id}", 100)
    wallet_id = wallet["id"]

    note1 = f"seq1-{run_id}"
    note2 = f"seq2-{run_id}"

    r1 = _post_withdrawal(wallet_id, 40, note1)
    assert r1.status_code == 200, (
        f"Expected HTTP 200 on first sequential withdrawal, got {r1.status_code}: {r1.text}"
    )
    r2 = _post_withdrawal(wallet_id, 25, note2)
    assert r2.status_code == 200, (
        f"Expected HTTP 200 on second sequential withdrawal, got {r2.status_code}: {r2.text}"
    )

    after = _get_wallet(wallet_id)
    assert float(after.get("balance", -1)) == 35, (
        f"Expected wallet balance to be 35 after two debits, got {after.get('balance')}"
    )

    # Use combined filter to verify both rows landed.
    r = requests.get(
        f"{BASE_URL}/api/collections/withdrawals/records",
        params={
            "filter": f'(note="{note1}"||note="{note2}")',
            "perPage": 50,
        },
        timeout=10,
    )
    assert r.status_code == 200, (
        f"Listing sequential withdrawals failed: {r.status_code} {r.text}"
    )
    assert int(r.json().get("totalItems", 0)) == 2, (
        f"Expected 2 persisted sequential withdrawal rows, got {r.json().get('totalItems')}"
    )


def test_insufficient_funds_rejected_and_atomic(start_app):
    run_id = _run_id()
    wallet = _create_wallet(f"wallet-insufficient-{run_id}", 50)
    wallet_id = wallet["id"]

    note = f"too-big-{run_id}"
    r = _post_withdrawal(wallet_id, 75, note)
    assert r.status_code == 400, (
        f"Expected HTTP 400 for insufficient funds, got {r.status_code}: {r.text}"
    )

    after = _get_wallet(wallet_id)
    assert float(after.get("balance", -1)) == 50, (
        f"Wallet balance must be unchanged after rejected withdrawal, got {after.get('balance')}"
    )
    assert _count_withdrawals_by_note(note) == 0, (
        f"No withdrawal row must be persisted for note {note!r}"
    )


def test_exact_balance_withdrawal_accepted(start_app):
    run_id = _run_id()
    wallet = _create_wallet(f"wallet-exact-{run_id}", 50)
    wallet_id = wallet["id"]

    note = f"exact-{run_id}"
    r = _post_withdrawal(wallet_id, 50, note)
    assert r.status_code == 200, (
        f"Expected HTTP 200 for exact-balance withdrawal, got {r.status_code}: {r.text}"
    )

    after = _get_wallet(wallet_id)
    assert float(after.get("balance", -1)) == 0, (
        f"Wallet balance must be exactly 0 after exact-balance withdrawal, got {after.get('balance')}"
    )
    assert _count_withdrawals_by_note(note) == 1, (
        f"Exactly one withdrawal row must exist for note {note!r}"
    )


def test_zero_or_negative_amount_rejected(start_app):
    run_id = _run_id()
    wallet = _create_wallet(f"wallet-nonpositive-{run_id}", 20)
    wallet_id = wallet["id"]

    note_zero = f"zero-{run_id}"
    note_neg = f"neg-{run_id}"

    r_zero = _post_withdrawal(wallet_id, 0, note_zero)
    assert r_zero.status_code == 400, (
        f"Expected HTTP 400 for amount=0, got {r_zero.status_code}: {r_zero.text}"
    )

    r_neg = _post_withdrawal(wallet_id, -5, note_neg)
    assert r_neg.status_code == 400, (
        f"Expected HTTP 400 for amount=-5, got {r_neg.status_code}: {r_neg.text}"
    )

    after = _get_wallet(wallet_id)
    assert float(after.get("balance", -1)) == 20, (
        f"Wallet balance must be unchanged after rejected non-positive withdrawals, got {after.get('balance')}"
    )
    assert _count_withdrawals_by_note(note_zero) == 0, (
        f"No withdrawal row must exist for note {note_zero!r}"
    )
    assert _count_withdrawals_by_note(note_neg) == 0, (
        f"No withdrawal row must exist for note {note_neg!r}"
    )


def test_unknown_wallet_rejected(start_app):
    run_id = _run_id()
    note = f"badwallet-{run_id}"

    r = _post_withdrawal("nonexistent00", 10, note)
    assert r.status_code == 400, (
        f"Expected HTTP 400 for unknown wallet id, got {r.status_code}: {r.text}"
    )
    assert _count_withdrawals_by_note(note) == 0, (
        f"No withdrawal row must exist for note {note!r}"
    )
