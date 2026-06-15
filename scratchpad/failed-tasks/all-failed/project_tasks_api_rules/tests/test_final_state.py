import os
import time
import subprocess
import socket
import requests
import pytest
from xprocess import ProcessStarter

PROJECT_DIR = "/home/user/app"

@pytest.fixture(scope="session")
def start_app(xprocess):
    class Starter(ProcessStarter):
        name = "start_app"
        args = ["./pocketbase", "serve", "--http=127.0.0.1:8090"]
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
def test_data(start_app):
    # Create superuser
    subprocess.run(
        ["./pocketbase", "superuser", "upsert", "admin@example.com", "Admin123456!"],
        cwd=PROJECT_DIR,
        check=True
    )
    
    # Authenticate as superuser
    resp = requests.post(
        "http://127.0.0.1:8090/api/collections/_superusers/auth-with-password",
        json={"identity": "admin@example.com", "password": "Admin123456!"}
    )
    assert resp.status_code == 200, f"Failed to login as admin: {resp.text}"
    admin_token = resp.json()["token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create user1
    resp = requests.post(
        "http://127.0.0.1:8090/api/collections/users/records",
        json={"username": "user1", "email": "user1@example.com", "password": "User123456!", "passwordConfirm": "User123456!"},
        headers=admin_headers
    )
    assert resp.status_code == 200, f"Failed to create user1: {resp.text}"
    user1_id = resp.json()["id"]
    
    # Create user2
    resp = requests.post(
        "http://127.0.0.1:8090/api/collections/users/records",
        json={"username": "user2", "email": "user2@example.com", "password": "User123456!", "passwordConfirm": "User123456!"},
        headers=admin_headers
    )
    assert resp.status_code == 200, f"Failed to create user2: {resp.text}"
    user2_id = resp.json()["id"]
    
    # Create project1
    resp = requests.post(
        "http://127.0.0.1:8090/api/collections/projects/records",
        json={"name": "Project 1", "members": [user1_id]},
        headers=admin_headers
    )
    assert resp.status_code == 200, f"Failed to create project1: {resp.text}"
    project1_id = resp.json()["id"]
    
    # Create task1
    resp = requests.post(
        "http://127.0.0.1:8090/api/collections/tasks/records",
        json={"title": "Task 1", "project": project1_id},
        headers=admin_headers
    )
    assert resp.status_code == 200, f"Failed to create task1: {resp.text}"
    task1_id = resp.json()["id"]
    
    # Get user1 token
    resp = requests.post(
        "http://127.0.0.1:8090/api/collections/users/auth-with-password",
        json={"identity": "user1@example.com", "password": "User123456!"}
    )
    assert resp.status_code == 200, f"Failed to login user1: {resp.text}"
    user1_token = resp.json()["token"]
    
    # Get user2 token
    resp = requests.post(
        "http://127.0.0.1:8090/api/collections/users/auth-with-password",
        json={"identity": "user2@example.com", "password": "User123456!"}
    )
    assert resp.status_code == 200, f"Failed to login user2: {resp.text}"
    user2_token = resp.json()["token"]
    
    return {
        "user1_token": user1_token,
        "user2_token": user2_token,
        "task1_id": task1_id
    }

def test_view_rule_authorized(test_data):
    headers = {"Authorization": f"Bearer {test_data['user1_token']}"}
    resp = requests.get(f"http://127.0.0.1:8090/api/collections/tasks/records/{test_data['task1_id']}", headers=headers)
    assert resp.status_code == 200, f"Expected 200 OK for authorized view, got {resp.status_code}: {resp.text}"
    assert resp.json()["id"] == test_data["task1_id"], "Response should contain the task"

def test_view_rule_unauthorized(test_data):
    headers = {"Authorization": f"Bearer {test_data['user2_token']}"}
    resp = requests.get(f"http://127.0.0.1:8090/api/collections/tasks/records/{test_data['task1_id']}", headers=headers)
    assert resp.status_code in [403, 404], f"Expected 403 or 404 for unauthorized view, got {resp.status_code}: {resp.text}"

def test_list_rule_authorized(test_data):
    headers = {"Authorization": f"Bearer {test_data['user1_token']}"}
    resp = requests.get("http://127.0.0.1:8090/api/collections/tasks/records", headers=headers)
    assert resp.status_code == 200, f"Expected 200 OK for authorized list, got {resp.status_code}: {resp.text}"
    items = resp.json().get("items", [])
    task_ids = [item["id"] for item in items]
    assert test_data["task1_id"] in task_ids, "Expected task1 to be in the list for user1"

def test_list_rule_unauthorized(test_data):
    headers = {"Authorization": f"Bearer {test_data['user2_token']}"}
    resp = requests.get("http://127.0.0.1:8090/api/collections/tasks/records", headers=headers)
    assert resp.status_code == 200, f"Expected 200 OK for unauthorized list, got {resp.status_code}: {resp.text}"
    items = resp.json().get("items", [])
    task_ids = [item["id"] for item in items]
    assert test_data["task1_id"] not in task_ids, "Expected task1 NOT to be in the list for user2"
