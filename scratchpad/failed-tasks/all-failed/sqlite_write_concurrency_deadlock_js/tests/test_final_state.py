import pytest
import subprocess
import os
import socket
import requests
import time
import concurrent.futures
from xprocess import ProcessStarter

PROJECT_DIR = "/home/user/pocketbase_app"
BASE_URL = "http://127.0.0.1:8090"

@pytest.fixture(scope="session")
def start_app(xprocess):
    class Starter(ProcessStarter):
        name = "pocketbase"
        args = ["./pocketbase", "serve", "--http=0.0.0.0:8090"]
        env = os.environ.copy()
        popen_kwargs = {
            "cwd": PROJECT_DIR,
            "text": True,
        }
        timeout = 180
        terminate_on_interrupt = True

        def startup_check(self):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(("localhost", 8090)) == 0

    xprocess.ensure(Starter.name, Starter)
    yield
    info = xprocess.getinfo(Starter.name)
    info.terminate()

@pytest.fixture(scope="session")
def admin_token(start_app):
    admin_email = "admin@example.com"
    admin_password = "adminpassword123"
    
    requests.post(f"{BASE_URL}/api/admins", json={
        "email": admin_email,
        "password": admin_password,
        "passwordConfirm": admin_password
    })
    
    resp = requests.post(f"{BASE_URL}/api/admins/auth-with-password", json={
        "identity": admin_email,
        "password": admin_password
    })
    assert resp.status_code == 200, f"Failed to auth admin: {resp.text}"
    return resp.json()["token"]

def create_user(admin_token, wallet_balance):
    headers = {"Authorization": admin_token}
    resp = requests.post(f"{BASE_URL}/api/collections/users/records", headers=headers, json={
        "email": f"user_{int(time.time() * 1000)}_{os.urandom(4).hex()}@example.com",
        "password": "password123",
        "passwordConfirm": "password123",
        "wallet": wallet_balance
    })
    assert resp.status_code == 200, f"Failed to create user: {resp.text}"
    return resp.json()["id"]

def test_insufficient_funds(start_app, admin_token):
    user_id = create_user(admin_token, 50)
    
    headers = {"Authorization": admin_token}
    resp = requests.post(f"{BASE_URL}/api/collections/orders/records", headers=headers, json={
        "user": user_id,
        "amount": 100
    })
    
    assert resp.status_code == 400, f"Expected 400 Bad Request, got {resp.status_code}"
    
    user_resp = requests.get(f"{BASE_URL}/api/collections/users/records/{user_id}", headers=headers)
    assert user_resp.json()["wallet"] == 50, "Wallet balance should not be changed"
    
    audit_resp = requests.get(f"{BASE_URL}/api/collections/audit_logs/records", headers=headers, params={
        "filter": f"user='{user_id}'"
    })
    assert len(audit_resp.json()["items"]) == 0, "No audit log should be created"

def test_successful_transaction(start_app, admin_token):
    user_id = create_user(admin_token, 200)
    
    headers = {"Authorization": admin_token}
    resp = requests.post(f"{BASE_URL}/api/collections/orders/records", headers=headers, json={
        "user": user_id,
        "amount": 50
    })
    
    assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}: {resp.text}"
    
    user_resp = requests.get(f"{BASE_URL}/api/collections/users/records/{user_id}", headers=headers)
    assert user_resp.json()["wallet"] == 150, "Wallet balance should be deducted"
    
    audit_resp = requests.get(f"{BASE_URL}/api/collections/audit_logs/records", headers=headers, params={
        "filter": f"user='{user_id}'"
    })
    items = audit_resp.json()["items"]
    assert len(items) == 1, "One audit log should be created"
    assert items[0]["action"] == "order_placed"
    assert items[0]["order_amount"] == 50

def test_concurrency_deadlock(start_app, admin_token):
    user_id = create_user(admin_token, 1000)
    headers = {"Authorization": admin_token}
    
    def create_order():
        return requests.post(f"{BASE_URL}/api/collections/orders/records", headers=headers, json={
            "user": user_id,
            "amount": 10
        })
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(create_order) for _ in range(5)]
        responses = [f.result() for f in concurrent.futures.as_completed(futures)]
        
    for resp in responses:
        assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}: {resp.text}"
        
    user_resp = requests.get(f"{BASE_URL}/api/collections/users/records/{user_id}", headers=headers)
    assert user_resp.json()["wallet"] == 950, "Wallet balance should be deducted exactly 5 times"
