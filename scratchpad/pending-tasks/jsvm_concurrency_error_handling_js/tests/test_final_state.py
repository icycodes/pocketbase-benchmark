import os
import socket
import pytest
import requests
from xprocess import ProcessStarter

PROJECT_DIR = "/home/user/pocketbase_app"

@pytest.fixture(scope="session")
def start_mock_webhook(xprocess):
    class Starter(ProcessStarter):
        name = "mock_webhook"
        args = ["python3", "mock_webhook.py"]
        env = os.environ.copy()
        popen_kwargs = {"cwd": PROJECT_DIR, "text": True}
        timeout = 10
        terminate_on_interrupt = True

        def startup_check(self):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(("127.0.0.1", 8081)) == 0

    xprocess.ensure(Starter.name, Starter)
    yield
    info = xprocess.getinfo(Starter.name)
    info.terminate()

@pytest.fixture(scope="session")
def start_pocketbase(xprocess, start_mock_webhook):
    class Starter(ProcessStarter):
        name = "pocketbase"
        args = ["./pocketbase", "serve", "--http=0.0.0.0:8090"]
        env = os.environ.copy()
        env["WEBHOOK_URL"] = "http://127.0.0.1:8081/webhook"
        popen_kwargs = {"cwd": PROJECT_DIR, "text": True}
        timeout = 10
        terminate_on_interrupt = True

        def startup_check(self):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(("127.0.0.1", 8090)) == 0

    xprocess.ensure(Starter.name, Starter)
    yield
    info = xprocess.getinfo(Starter.name)
    info.terminate()

def test_webhook_success_case(start_pocketbase):
    url = "http://127.0.0.1:8090/api/collections/users/records"
    payload = {
        "email": "success@example.com",
        "password": "password123",
        "passwordConfirm": "password123"
    }
    response = requests.post(url, json=payload)
    assert response.status_code == 200, f"Expected status 200, got {response.status_code}. Response: {response.text}"
    data = response.json()
    assert data.get("email") == "success@example.com", "Expected created user record with email success@example.com"

def test_webhook_failure_case(start_pocketbase):
    url = "http://127.0.0.1:8090/api/collections/users/records"
    payload = {
        "email": "fail@example.com",
        "password": "password123",
        "passwordConfirm": "password123"
    }
    response = requests.post(url, json=payload)
    assert response.status_code == 400, f"Expected status 400, got {response.status_code}. Response: {response.text}"
    assert "Webhook failed" in response.text, f"Expected 'Webhook failed' in error message, got: {response.text}"

    # Verify user was not created
    get_url = "http://127.0.0.1:8090/api/collections/users/records"
    params = {"filter": "(email='fail@example.com')"}
    get_response = requests.get(get_url, params=params)
    assert get_response.status_code == 200, f"Expected status 200 on GET, got {get_response.status_code}"
    get_data = get_response.json()
    assert len(get_data.get("items", [])) == 0, f"Expected empty items array, meaning user was not created, got {get_data}"
