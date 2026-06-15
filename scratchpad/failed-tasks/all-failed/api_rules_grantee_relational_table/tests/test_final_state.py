import os
import pytest
import requests
import socket
import subprocess
from xprocess import ProcessStarter

PROJECT_DIR = "/home/user/myproject"
PB_URL = "http://localhost:8090"

@pytest.fixture(scope="session")
def setup_admin():
    """Create an admin user before starting the server so we can use the API."""
    # Create admin via CLI
    subprocess.run(
        ["./pocketbase", "admin", "create", "admin@example.com", "Admin12345678!"],
        cwd=PROJECT_DIR,
        capture_output=True,
    )
    yield "admin@example.com", "Admin12345678!"

@pytest.fixture(scope="session")
def start_app(xprocess, setup_admin):
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
def admin_token(start_app, setup_admin):
    email, password = setup_admin
    resp = requests.post(f"{PB_URL}/api/admins/auth-with-password", json={
        "identity": email,
        "password": password
    })
    assert resp.status_code == 200, f"Failed to authenticate admin: {resp.text}"
    return resp.json()["token"]

def create_user(admin_token, username, password):
    resp = requests.post(f"{PB_URL}/api/collections/users/records", headers={
        "Authorization": admin_token
    }, json={
        "username": username,
        "password": password,
        "passwordConfirm": password,
        "email": f"{username}@example.com"
    })
    assert resp.status_code == 200, f"Failed to create user {username}: {resp.text}"
    return resp.json()["id"]

def get_user_token(username, password):
    resp = requests.post(f"{PB_URL}/api/collections/users/auth-with-password", json={
        "identity": username,
        "password": password
    })
    assert resp.status_code == 200, f"Failed to authenticate user {username}: {resp.text}"
    return resp.json()["token"]

def test_api_rules_grantee_relational_table(start_app, admin_token):
    # 1. Create Test Users
    userA_id = create_user(admin_token, "userA", "password123")
    userB_id = create_user(admin_token, "userB", "password123")
    userC_id = create_user(admin_token, "userC", "password123")

    tokenA = get_user_token("userA", "password123")
    tokenB = get_user_token("userB", "password123")
    tokenC = get_user_token("userC", "password123")

    # 2. Create Document
    doc_resp = requests.post(f"{PB_URL}/api/collections/documents/records", headers={
        "Authorization": admin_token
    }, json={
        "title": "Secret Plan",
        "author": userA_id
    })
    assert doc_resp.status_code == 200, f"Failed to create document: {doc_resp.text}"
    doc_id = doc_resp.json()["id"]

    # 3. Create Permission
    perm_resp = requests.post(f"{PB_URL}/api/collections/document_edit_permissions/records", headers={
        "Authorization": admin_token
    }, json={
        "document": doc_id,
        "grantee": userB_id
    })
    assert perm_resp.status_code == 200, f"Failed to create permission: {perm_resp.text}"

    # 4. Test Update as Author (userA)
    updateA_resp = requests.patch(f"{PB_URL}/api/collections/documents/records/{doc_id}", headers={
        "Authorization": tokenA
    }, json={
        "title": "Updated by Author"
    })
    assert updateA_resp.status_code == 200, f"Update by author failed: {updateA_resp.text}"

    # 5. Test Update as Grantee (userB)
    updateB_resp = requests.patch(f"{PB_URL}/api/collections/documents/records/{doc_id}", headers={
        "Authorization": tokenB
    }, json={
        "title": "Updated by Grantee"
    })
    assert updateB_resp.status_code == 200, f"Update by grantee failed: {updateB_resp.text}"

    # 6. Test Update as Unauthorized (userC)
    updateC_resp = requests.patch(f"{PB_URL}/api/collections/documents/records/{doc_id}", headers={
        "Authorization": tokenC
    }, json={
        "title": "Hacked"
    })
    assert updateC_resp.status_code in [400, 403, 404], f"Unauthorized update should have failed, but got {updateC_resp.status_code}"
