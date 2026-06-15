import os
import time
import pytest
import requests
import socket
from xprocess import ProcessStarter

PROJECT_DIR = "/home/user/myproject"
BASE_URL = "http://127.0.0.1:8090"

@pytest.fixture(scope="session")
def start_app(xprocess):
    class Starter(ProcessStarter):
        name = "pocketbase_server"
        args = ["./pocketbase", "serve", "--http=0.0.0.0:8090"]
        env = os.environ.copy()
        popen_kwargs = {
            "cwd": PROJECT_DIR,
            "text": True,
        }
        timeout = 30
        terminate_on_interrupt = True

        def startup_check(self):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(("127.0.0.1", 8090)) == 0

    xprocess.ensure(Starter.name, Starter)
    yield
    info = xprocess.getinfo(Starter.name)
    info.terminate()

@pytest.fixture(scope="session")
def test_data_setup(start_app):
    # Create user 1
    resp1 = requests.post(f"{BASE_URL}/api/collections/users/records", json={
        "username": "testuser1",
        "password": "password123",
        "passwordConfirm": "password123",
        "email": "test1@example.com"
    })
    assert resp1.status_code == 200, f"Failed to create user 1: {resp1.text}"
    user_id_1 = resp1.json()["id"]

    # Create user 2
    resp2 = requests.post(f"{BASE_URL}/api/collections/users/records", json={
        "username": "testuser2",
        "password": "password123",
        "passwordConfirm": "password123",
        "email": "test2@example.com"
    })
    assert resp2.status_code == 200, f"Failed to create user 2: {resp2.text}"
    user_id_2 = resp2.json()["id"]

    # Create posts for user 1
    r_post1 = requests.post(f"{BASE_URL}/api/collections/posts/records", json={
        "title": "Post 1",
        "author": user_id_1
    })
    assert r_post1.status_code == 200, f"Failed to create post 1: {r_post1.text}"

    r_post2 = requests.post(f"{BASE_URL}/api/collections/posts/records", json={
        "title": "Post 2",
        "author": user_id_1
    })
    assert r_post2.status_code == 200, f"Failed to create post 2: {r_post2.text}"

    # Create post for user 2
    r_post3 = requests.post(f"{BASE_URL}/api/collections/posts/records", json={
        "title": "Post 3",
        "author": user_id_2
    })
    assert r_post3.status_code == 200, f"Failed to create post 3: {r_post3.text}"

    return {
        "user_id_1": user_id_1,
        "user_id_2": user_id_2
    }

def test_view_collection_user_post_counts(start_app, test_data_setup):
    user_id_1 = test_data_setup["user_id_1"]
    user_id_2 = test_data_setup["user_id_2"]

    resp = requests.get(f"{BASE_URL}/api/collections/user_post_counts/records")
    assert resp.status_code == 200, f"Failed to query view collection: {resp.text}"

    data = resp.json()
    items = data.get("items", [])

    user1_found = False
    user2_found = False

    for item in items:
        if item.get("id") == user_id_1:
            assert item.get("username") == "testuser1", f"Expected username testuser1, got {item.get('username')}"
            assert item.get("post_count") == 2, f"Expected post_count 2 for user_id_1, got {item.get('post_count')}"
            user1_found = True
        elif item.get("id") == user_id_2:
            assert item.get("username") == "testuser2", f"Expected username testuser2, got {item.get('username')}"
            assert item.get("post_count") == 1, f"Expected post_count 1 for user_id_2, got {item.get('post_count')}"
            user2_found = True

    assert user1_found, f"User 1 (id: {user_id_1}) not found in view collection results."
    assert user2_found, f"User 2 (id: {user_id_2}) not found in view collection results."
