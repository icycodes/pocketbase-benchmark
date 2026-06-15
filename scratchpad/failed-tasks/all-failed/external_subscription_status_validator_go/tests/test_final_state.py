import os
import subprocess
import socket
import pytest
import requests
from xprocess import ProcessStarter

PROJECT_DIR = "/home/user/myproject"

@pytest.fixture(scope="session")
def start_mock_server(xprocess):
    class MockStarter(ProcessStarter):
        name = "mock_server"
        args = ["python3", "/home/user/mock_server.py"]
        env = os.environ.copy()
        timeout = 30
        terminate_on_interrupt = True

        def startup_check(self):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(("localhost", 8080)) == 0

    xprocess.ensure(MockStarter.name, MockStarter)
    yield
    info = xprocess.getinfo(MockStarter.name)
    info.terminate()

@pytest.fixture(scope="session")
def start_pocketbase(xprocess, start_mock_server):
    # Ensure dependencies are tidy
    subprocess.run(["go", "mod", "tidy"], cwd=PROJECT_DIR, check=True)

    class PBStarter(ProcessStarter):
        name = "pocketbase"
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

    xprocess.ensure(PBStarter.name, PBStarter)
    yield
    info = xprocess.getinfo(PBStarter.name)
    info.terminate()

def test_create_post_active_subscription(start_pocketbase):
    """Test creating a post with an active subscription."""
    payload = {"title": "First Post", "author": "active_user"}
    response = requests.post("http://localhost:8090/api/collections/posts/records", json=payload)
    
    assert response.status_code == 200, f"Expected status 200, got {response.status_code}. Response: {response.text}"
    data = response.json()
    assert data.get("title") == "First Post", f"Expected title 'First Post', got {data.get('title')}"
    assert data.get("author") == "active_user", f"Expected author 'active_user', got {data.get('author')}"

def test_create_post_inactive_subscription(start_pocketbase):
    """Test creating a post with an inactive subscription."""
    payload = {"title": "Second Post", "author": "inactive_user"}
    response = requests.post("http://localhost:8090/api/collections/posts/records", json=payload)
    
    assert response.status_code == 400, f"Expected status 400, got {response.status_code}. Response: {response.text}"

def test_create_post_missing_subscription(start_pocketbase):
    """Test creating a post with a missing/error subscription."""
    payload = {"title": "Third Post", "author": "unknown_user"}
    response = requests.post("http://localhost:8090/api/collections/posts/records", json=payload)
    
    assert response.status_code == 400, f"Expected status 400, got {response.status_code}. Response: {response.text}"
