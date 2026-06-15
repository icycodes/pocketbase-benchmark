import pytest
import os
import socket
import requests
from xprocess import ProcessStarter

PROJECT_DIR = "/workspace/pb"

@pytest.fixture(scope="session")
def start_app(xprocess):
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

def test_rate_limited_signup(start_app):
    url = "http://localhost:8090/api/custom_signup"
    
    # 1. First 5 Requests (Success)
    for i in range(1, 6):
        payload = {
            "email": f"test{i}@example.com",
            "password": "password12345",
            "passwordConfirm": "password12345"
        }
        response = requests.post(url, json=payload)
        assert response.status_code in (200, 201), f"Request {i} failed with status {response.status_code}: {response.text}"
    
    # 2. 6th Request (Rate Limited)
    payload = {
        "email": "test6@example.com",
        "password": "password12345",
        "passwordConfirm": "password12345"
    }
    response = requests.post(url, json=payload)
    assert response.status_code == 429, f"Expected status 429 for 6th request, got {response.status_code}: {response.text}"

def test_users_created(start_app):
    # Verify that the first 5 users were actually created by authenticating as them
    auth_url = "http://localhost:8090/api/collections/users/auth-with-password"
    
    for i in range(1, 6):
        payload = {
            "identity": f"test{i}@example.com",
            "password": "password12345"
        }
        response = requests.post(auth_url, json=payload)
        assert response.status_code == 200, f"Failed to authenticate as test{i}@example.com, user might not have been created properly: {response.text}"
