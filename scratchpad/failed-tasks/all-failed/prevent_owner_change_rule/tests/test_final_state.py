import pytest
import subprocess
import os
import socket
import requests
from xprocess import ProcessStarter

PROJECT_DIR = "/home/user/myproject"
PB_URL = "http://localhost:8090"

@pytest.fixture(scope="session")
def start_app(xprocess):
    # Before starting, create a superuser
    subprocess.run(
        ["go", "run", "main.go", "superuser", "upsert", "admin@example.com", "admin123456"],
        cwd=PROJECT_DIR, check=True
    )

    class Starter(ProcessStarter):
        name = "start_app"
        args = ["go", "run", "main.go", "serve", "--http=0.0.0.0:8090"]
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

def test_prevent_owner_change_rule(start_app):
    # 1. Auth as superuser
    resp = requests.post(f"{PB_URL}/api/collections/_superusers/auth-with-password", json={
        "identity": "admin@example.com",
        "password": "admin123456"
    })
    assert resp.status_code == 200, f"Failed to auth as superuser: {resp.text}"
    admin_token = resp.json()["token"]
    admin_headers = {"Authorization": admin_token}

    # 2. Create userA and userB
    respA = requests.post(f"{PB_URL}/api/collections/users/records", json={
        "email": "usera@example.com",
        "password": "password123",
        "passwordConfirm": "password123"
    }, headers=admin_headers)
    assert respA.status_code == 200, f"Failed to create userA: {respA.text}"
    userA_id = respA.json()["id"]

    respB = requests.post(f"{PB_URL}/api/collections/users/records", json={
        "email": "userb@example.com",
        "password": "password123",
        "passwordConfirm": "password123"
    }, headers=admin_headers)
    assert respB.status_code == 200, f"Failed to create userB: {respB.text}"
    userB_id = respB.json()["id"]

    # 3. Create a post owned by userA
    resp_post = requests.post(f"{PB_URL}/api/collections/posts/records", json={
        "title": "Original Title",
        "owner": userA_id
    }, headers=admin_headers)
    assert resp_post.status_code == 200, f"Failed to create post: {resp_post.text}"
    post_id = resp_post.json()["id"]

    # 4. Authenticate as userA
    resp_authA = requests.post(f"{PB_URL}/api/collections/users/auth-with-password", json={
        "identity": "usera@example.com",
        "password": "password123"
    })
    assert resp_authA.status_code == 200, f"Failed to auth userA: {resp_authA.text}"
    userA_token = resp_authA.json()["token"]
    userA_headers = {"Authorization": userA_token}

    # 5. Authenticate as userB
    resp_authB = requests.post(f"{PB_URL}/api/collections/users/auth-with-password", json={
        "identity": "userb@example.com",
        "password": "password123"
    })
    assert resp_authB.status_code == 200, f"Failed to auth userB: {resp_authB.text}"
    userB_token = resp_authB.json()["token"]
    userB_headers = {"Authorization": userB_token}

    # Verification Step 2: Valid Update by Owner
    patch1 = requests.patch(f"{PB_URL}/api/collections/posts/records/{post_id}", json={
        "title": "Updated Title"
    }, headers=userA_headers)
    assert patch1.status_code == 200, f"Valid update by owner failed: {patch1.text}"

    # Verification Step 3: Invalid Update: Changing Owner
    patch2 = requests.patch(f"{PB_URL}/api/collections/posts/records/{post_id}", json={
        "owner": userB_id
    }, headers=userA_headers)
    assert patch2.status_code in [400, 403], f"Update changing owner should fail, got {patch2.status_code}"

    # Verification Step 4: Invalid Update by Non-Owner
    patch3 = requests.patch(f"{PB_URL}/api/collections/posts/records/{post_id}", json={
        "title": "Hacked Title"
    }, headers=userB_headers)
    assert patch3.status_code in [403, 404], f"Update by non-owner should fail, got {patch3.status_code}"
