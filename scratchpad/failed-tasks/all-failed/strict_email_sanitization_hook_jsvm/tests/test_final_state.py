import pytest
import os
import socket
import requests
from xprocess import ProcessStarter

PROJECT_DIR = "/home/user/myproject"

@pytest.fixture(scope="session")
def start_pocketbase(xprocess):
    """Starts PocketBase and waits until it listens on port 8090."""
    class Starter(ProcessStarter):
        name = "pocketbase"
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
                return s.connect_ex(("localhost", 8090)) == 0

    xprocess.ensure(Starter.name, Starter)
    yield
    info = xprocess.getinfo(Starter.name)
    info.terminate()

def test_email_sanitization_on_create(start_pocketbase):
    # 1. Create User with Unsanitized Email
    create_url = "http://localhost:8090/api/collections/users/records"
    payload = {
        "email": "  John.Doe@EXAMPLE.com  ",
        "password": "secure_password123",
        "passwordConfirm": "secure_password123"
    }
    
    response = requests.post(create_url, json=payload)
    assert response.status_code == 200, f"Expected status 200 on user creation, got {response.status_code}. Response: {response.text}"
    
    data = response.json()
    assert "email" in data, "Response JSON does not contain 'email' field."
    assert data["email"] == "john.doe@example.com", f"Expected email to be sanitized to 'john.doe@example.com', got '{data['email']}'"
    
    created_user_id = data.get("id")
    assert created_user_id, "Response JSON does not contain 'id' field."
    
    # 2. Verify Persisted State
    get_url = f"http://localhost:8090/api/collections/users/records/{created_user_id}"
    get_response = requests.get(get_url)
    assert get_response.status_code == 200, f"Expected status 200 on user retrieval, got {get_response.status_code}. Response: {get_response.text}"
    
    get_data = get_response.json()
    assert "email" in get_data, "Response JSON does not contain 'email' field on GET."
    assert get_data["email"] == "john.doe@example.com", f"Expected persisted email to be 'john.doe@example.com', got '{get_data['email']}'"
