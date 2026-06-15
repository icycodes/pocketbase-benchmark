import os
import socket
import pytest
import requests
from xprocess import ProcessStarter

PROJECT_DIR = "/home/user/myproject"
BASE_URL = "http://127.0.0.1:8090"

@pytest.fixture(scope="session")
def start_app(xprocess):
    class Starter(ProcessStarter):
        name = "pocketbase_app"
        args = ["./pocketbase", "serve", "--http=0.0.0.0:8090"]
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

def auth_user(email, password):
    url = f"{BASE_URL}/api/collections/users/auth-with-password"
    data = {
        "identity": email,
        "password": password
    }
    resp = requests.post(url, json=data)
    assert resp.status_code == 200, f"Failed to auth user {email}: {resp.text}"
    return resp.json()["token"]

def test_relational_access_control(start_app):
    # Create admin
    admin_email = "admin@example.com"
    admin_password = "adminpassword123"
    
    # Check if admin already exists
    admin_auth_url = f"{BASE_URL}/api/admins/auth-with-password"
    admin_auth_resp = requests.post(admin_auth_url, json={
        "identity": admin_email,
        "password": admin_password
    })
    
    if admin_auth_resp.status_code != 200:
        admin_url = f"{BASE_URL}/api/admins"
        admin_resp = requests.post(admin_url, json={
            "email": admin_email,
            "password": admin_password,
            "passwordConfirm": admin_password
        })
        assert admin_resp.status_code == 200, f"Failed to create admin: {admin_resp.text}"
        admin_auth_resp = requests.post(admin_auth_url, json={
            "identity": admin_email,
            "password": admin_password
        })
        assert admin_auth_resp.status_code == 200, f"Failed to auth admin: {admin_auth_resp.text}"

    admin_token = admin_auth_resp.json()["token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    def admin_create(collection, data):
        resp = requests.post(f"{BASE_URL}/api/collections/{collection}/records", json=data, headers=admin_headers)
        assert resp.status_code == 200, f"Admin failed to create {collection}: {resp.text}"
        return resp.json()["id"]

    # 1. Create Test Users (via Admin API to bypass rules)
    userA_id = admin_create("users", {
        "email": "userA@example.com",
        "password": "password123",
        "passwordConfirm": "password123"
    })
    userB_id = admin_create("users", {
        "email": "userB@example.com",
        "password": "password123",
        "passwordConfirm": "password123"
    })

    # 2. Create Projects (via Admin API)
    project1_id = admin_create("projects", {"name": "Project Alpha", "members": [userA_id]})
    project2_id = admin_create("projects", {"name": "Project Beta", "members": [userB_id]})

    # 3. Create Tasks (via Admin API)
    task1_id = admin_create("tasks", {"title": "Task Alpha", "project": project1_id})
    task2_id = admin_create("tasks", {"title": "Task Beta", "project": project2_id})

    # 4. Verify Access for User A
    tokenA = auth_user("userA@example.com", "password123")
    headersA = {"Authorization": f"Bearer {tokenA}"}
    
    # List Tasks
    respA_list = requests.get(f"{BASE_URL}/api/collections/tasks/records", headers=headersA)
    assert respA_list.status_code == 200, f"User A failed to list tasks: {respA_list.text}"
    tasksA = respA_list.json()["items"]
    taskA_ids = [t["id"] for t in tasksA]
    assert task1_id in taskA_ids, "User A should see Task 1"
    assert task2_id not in taskA_ids, "User A should NOT see Task 2"

    # View Task 1
    respA_view1 = requests.get(f"{BASE_URL}/api/collections/tasks/records/{task1_id}", headers=headersA)
    assert respA_view1.status_code == 200, "User A should be able to view Task 1"

    # View Task 2
    respA_view2 = requests.get(f"{BASE_URL}/api/collections/tasks/records/{task2_id}", headers=headersA)
    assert respA_view2.status_code in [403, 404], "User A should NOT be able to view Task 2 (expected 403 or 404)"

    # 5. Verify Access for User B
    tokenB = auth_user("userB@example.com", "password123")
    headersB = {"Authorization": f"Bearer {tokenB}"}
    
    # List Tasks
    respB_list = requests.get(f"{BASE_URL}/api/collections/tasks/records", headers=headersB)
    assert respB_list.status_code == 200, f"User B failed to list tasks: {respB_list.text}"
    tasksB = respB_list.json()["items"]
    taskB_ids = [t["id"] for t in tasksB]
    assert task2_id in taskB_ids, "User B should see Task 2"
    assert task1_id not in taskB_ids, "User B should NOT see Task 1"
