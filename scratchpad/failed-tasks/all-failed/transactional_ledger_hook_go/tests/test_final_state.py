import pytest
import subprocess
import os
import socket
import requests
from xprocess import ProcessStarter

PROJECT_DIR = "/home/user/myproject"

@pytest.fixture(scope="session")
def start_app(xprocess):
    # Run go mod tidy before starting the server
    subprocess.run(["go", "mod", "tidy"], cwd=PROJECT_DIR, check=True)

    class Starter(ProcessStarter):
        name = "start_app"
        args = ["go", "run", "main.go", "serve", "--http=0.0.0.0:8090"]
        env = os.environ.copy()
        popen_kwargs = {
            "cwd": PROJECT_DIR,
            "text": True,
        }
        timeout = 60
        terminate_on_interrupt = True

        def startup_check(self):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(("127.0.0.1", 8090)) == 0

    xprocess.ensure(Starter.name, Starter)
    yield
    info = xprocess.getinfo(Starter.name)
    info.terminate()

def test_sufficient_funds_withdrawal(start_app):
    response = requests.post(
        "http://127.0.0.1:8090/api/withdraw",
        json={"wallet_id": "walletrich00000", "amount": 50}
    )
    assert response.status_code == 200, f"Expected status 200, got {response.status_code}. Response: {response.text}"

def test_verify_wallet_balance_deducted(start_app):
    response = requests.get("http://127.0.0.1:8090/api/collections/wallets/records/walletrich00000")
    assert response.status_code == 200, f"Expected status 200, got {response.status_code}. Response: {response.text}"
    data = response.json()
    assert data.get("balance") == 50, f"Expected balance to be 50, got {data.get('balance')}"

def test_verify_ledger_record_created(start_app):
    response = requests.get("http://127.0.0.1:8090/api/collections/ledger/records?filter=(wallet_id='walletrich00000')")
    assert response.status_code == 200, f"Expected status 200, got {response.status_code}. Response: {response.text}"
    data = response.json()
    items = data.get("items", [])
    assert len(items) == 1, f"Expected 1 ledger record, got {len(items)}"
    assert items[0].get("amount") == 50, f"Expected ledger amount to be 50, got {items[0].get('amount')}"

def test_insufficient_funds_withdrawal(start_app):
    response = requests.post(
        "http://127.0.0.1:8090/api/withdraw",
        json={"wallet_id": "walletpoor00000", "amount": 50}
    )
    assert response.status_code == 400, f"Expected status 400, got {response.status_code}. Response: {response.text}"

def test_verify_poor_wallet_balance_unchanged(start_app):
    response = requests.get("http://127.0.0.1:8090/api/collections/wallets/records/walletpoor00000")
    assert response.status_code == 200, f"Expected status 200, got {response.status_code}. Response: {response.text}"
    data = response.json()
    assert data.get("balance") == 10, f"Expected balance to be 10, got {data.get('balance')}"

def test_verify_no_ledger_record_created(start_app):
    response = requests.get("http://127.0.0.1:8090/api/collections/ledger/records?filter=(wallet_id='walletpoor00000')")
    assert response.status_code == 200, f"Expected status 200, got {response.status_code}. Response: {response.text}"
    data = response.json()
    items = data.get("items", [])
    assert len(items) == 0, f"Expected 0 ledger records, got {len(items)}"
