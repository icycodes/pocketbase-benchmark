import os
import subprocess
import socket
import time
import requests
import pytest
from xprocess import ProcessStarter

PROJECT_DIR = "/home/user/myproject"
BASE_URL = "http://localhost:8090"

@pytest.fixture(scope="session")
def start_app(xprocess):
    # Create a superuser first
    subprocess.run(
        ["./pocketbase", "superuser", "create", "admin@example.com", "AdminPass123!"],
        cwd=PROJECT_DIR,
        capture_output=True,
    )

    class Starter(ProcessStarter):
        name = "pocketbase_server"
        args = ["./pocketbase", "serve", "--http=0.0.0.0:8090"]
        env = os.environ.copy()
        popen_kwargs = {"cwd": PROJECT_DIR, "text": True}
        timeout = 30
        terminate_on_interrupt = True

        def startup_check(self):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(("localhost", 8090)) == 0

    xprocess.ensure(Starter.name, Starter)
    yield
    info = xprocess.getinfo(Starter.name)
    info.terminate()

@pytest.fixture(scope="session")
def setup_data(start_app):
    # Authenticate as superuser
    resp = requests.post(
        f"{BASE_URL}/api/collections/_superusers/auth-with-password",
        json={"identity": "admin@example.com", "password": "AdminPass123!"}
    )
    assert resp.status_code == 200, f"Superuser login failed: {resp.text}"
    admin_token = resp.json()["token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Create users
    users = ["u_owner@example.com", "u_editor@example.com", "u_viewer@example.com", "u_outsider@example.com"]
    user_ids = {}
    for email in users:
        r = requests.post(
            f"{BASE_URL}/api/collections/users/records",
            json={"email": email, "password": "password123", "passwordConfirm": "password123"},
            headers=headers
        )
        assert r.status_code == 200, f"Failed to create user {email}: {r.text}"
        user_ids[email] = r.json()["id"]

    # Create organization
    r = requests.post(
        f"{BASE_URL}/api/collections/organizations/records",
        json={"name": "Test Org"},
        headers=headers
    )
    assert r.status_code == 200, f"Failed to create organization: {r.text}"
    org_id = r.json()["id"]

    # Create organization_members
    roles = {
        "u_owner@example.com": "owner",
        "u_editor@example.com": "editor",
        "u_viewer@example.com": "viewer"
    }
    for email, role in roles.items():
        r = requests.post(
            f"{BASE_URL}/api/collections/organization_members/records",
            json={"user": user_ids[email], "organization": org_id, "role": role},
            headers=headers
        )
        assert r.status_code == 200, f"Failed to create member {email}: {r.text}"

    return {"user_ids": user_ids, "org_id": org_id}

def auth_as(email):
    resp = requests.post(
        f"{BASE_URL}/api/collections/users/auth-with-password",
        json={"identity": email, "password": "password123"}
    )
    assert resp.status_code == 200, f"Failed to authenticate as {email}: {resp.text}"
    return resp.json()["token"]

def test_permissions(setup_data):
    org_id = setup_data["org_id"]
    
    # Authenticate users
    editor_token = auth_as("u_editor@example.com")
    viewer_token = auth_as("u_viewer@example.com")
    outsider_token = auth_as("u_outsider@example.com")
    owner_token = auth_as("u_owner@example.com")

    # 1. Test Create (Editor)
    r = requests.post(
        f"{BASE_URL}/api/collections/documents/records",
        json={"title": "Doc 1", "content": "Content", "organization": org_id},
        headers={"Authorization": f"Bearer {editor_token}"}
    )
    assert r.status_code == 200, f"Editor should be able to create document. Got: {r.text}"
    doc_id = r.json()["id"]

    # 2. Test Create (Viewer)
    r = requests.post(
        f"{BASE_URL}/api/collections/documents/records",
        json={"title": "Doc 2", "content": "Content", "organization": org_id},
        headers={"Authorization": f"Bearer {viewer_token}"}
    )
    assert r.status_code in [400, 403], f"Viewer should not be able to create document. Got: {r.status_code}"

    # 3. Test Read (Viewer)
    r = requests.get(
        f"{BASE_URL}/api/collections/documents/records/{doc_id}",
        headers={"Authorization": f"Bearer {viewer_token}"}
    )
    assert r.status_code == 200, f"Viewer should be able to read document. Got: {r.text}"

    # 4. Test Read (Outsider)
    r = requests.get(
        f"{BASE_URL}/api/collections/documents/records/{doc_id}",
        headers={"Authorization": f"Bearer {outsider_token}"}
    )
    assert r.status_code in [403, 404], f"Outsider should not be able to read document. Got: {r.status_code}"

    # 5. Test Update (Viewer)
    r = requests.patch(
        f"{BASE_URL}/api/collections/documents/records/{doc_id}",
        json={"title": "Updated by Viewer"},
        headers={"Authorization": f"Bearer {viewer_token}"}
    )
    assert r.status_code in [400, 403, 404], f"Viewer should not be able to update document. Got: {r.status_code}"

    # 6. Test Update (Editor)
    r = requests.patch(
        f"{BASE_URL}/api/collections/documents/records/{doc_id}",
        json={"title": "Updated by Editor"},
        headers={"Authorization": f"Bearer {editor_token}"}
    )
    assert r.status_code == 200, f"Editor should be able to update document. Got: {r.text}"

    # 7. Test Delete (Editor)
    r = requests.delete(
        f"{BASE_URL}/api/collections/documents/records/{doc_id}",
        headers={"Authorization": f"Bearer {editor_token}"}
    )
    assert r.status_code in [400, 403, 404], f"Editor should not be able to delete document. Got: {r.status_code}"

    # 8. Test Delete (Owner)
    r = requests.delete(
        f"{BASE_URL}/api/collections/documents/records/{doc_id}",
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert r.status_code in [200, 204], f"Owner should be able to delete document. Got: {r.text}"
