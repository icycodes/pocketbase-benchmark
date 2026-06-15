import pytest
import requests
import os
import socket
import concurrent.futures
from xprocess import ProcessStarter

PROJECT_DIR = "/home/user/app"
BASE_URL = "http://localhost:8090"

@pytest.fixture(scope="session")
def build_app():
    import subprocess
    result = subprocess.run(["go", "build", "-o", "main", "."], cwd=PROJECT_DIR, capture_output=True, text=True)
    assert result.returncode == 0, f"Failed to build app: {result.stderr}"
    yield

@pytest.fixture(scope="session")
def start_app(build_app, xprocess):
    class Starter(ProcessStarter):
        name = "pocketbase_app"
        args = ["./main", "serve", "--http=0.0.0.0:8090"]
        env = os.environ.copy()
        popen_kwargs = {
            "cwd": PROJECT_DIR,
            "text": True,
        }
        timeout = 60
        terminate_on_interrupt = True

        def startup_check(self):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(("localhost", 8090)) == 0

    xprocess.ensure(Starter.name, Starter)
    yield
    info = xprocess.getinfo(Starter.name)
    info.terminate()

def test_concurrent_withdrawals(start_app):
    # 1. Create a wallet with balance 50
    wallet_resp = requests.post(f"{BASE_URL}/api/collections/wallets/records", json={"balance": 50})
    assert wallet_resp.status_code == 200, f"Failed to create wallet: {wallet_resp.text}"
    wallet_id = wallet_resp.json().get("id")
    assert wallet_id is not None, "Wallet ID not found in response"

    # 2. Send 10 concurrent requests to withdraw 10
    def withdraw():
        return requests.post(
            f"{BASE_URL}/api/collections/withdrawals/records",
            json={"wallet_id": wallet_id, "amount": 10}
        )

    success_count = 0
    fail_count = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(withdraw) for _ in range(10)]
        for future in concurrent.futures.as_completed(futures):
            resp = future.result()
            if resp.status_code == 200:
                success_count += 1
            elif resp.status_code == 400:
                fail_count += 1
            else:
                pytest.fail(f"Unexpected status code {resp.status_code}: {resp.text}")

    assert success_count == 5, f"Expected exactly 5 successful withdrawals, got {success_count}"
    assert fail_count == 5, f"Expected exactly 5 failed withdrawals, got {fail_count}"

    # 3. Verify final balance is 0
    wallet_check_resp = requests.get(f"{BASE_URL}/api/collections/wallets/records/{wallet_id}")
    assert wallet_check_resp.status_code == 200, f"Failed to fetch wallet: {wallet_check_resp.text}"
    final_balance = wallet_check_resp.json().get("balance")
    assert final_balance == 0, f"Expected final balance to be 0, got {final_balance}"

    # 4. Verify exactly 5 withdrawal records exist
    withdrawals_resp = requests.get(f"{BASE_URL}/api/collections/withdrawals/records", params={"filter": f"wallet_id='{wallet_id}'"})
    assert withdrawals_resp.status_code == 200, f"Failed to fetch withdrawals: {withdrawals_resp.text}"
    withdrawals_count = withdrawals_resp.json().get("totalItems", len(withdrawals_resp.json().get("items", [])))
    assert withdrawals_count == 5, f"Expected exactly 5 withdrawal records, got {withdrawals_count}"