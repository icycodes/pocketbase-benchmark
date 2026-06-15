import os
import socket
import pytest
import requests
from xprocess import ProcessStarter

PROJECT_DIR = "/home/user/pocketbase"
PORT = 8090

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
        timeout = 180
        terminate_on_interrupt = True

        def startup_check(self):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(("localhost", PORT)) == 0

    xprocess.ensure(Starter.name, Starter)
    yield
    info = xprocess.getinfo(Starter.name)
    info.terminate()

def test_email_sanitization_hook(start_app):
    # Step 1: Create User with Unsanitized Email
    create_url = f"http://localhost:{PORT}/api/collections/users/records"
    create_payload = {
        "email": "  TEST.user1@EXAMPLE.com  ",
        "password": "password123",
        "passwordConfirm": "password123"
    }
    
    create_response = requests.post(create_url, json=create_payload)
    assert create_response.status_code == 200, f"Failed to create user: {create_response.text}"
    
    create_data = create_response.json()
    assert create_data.get("email") == "test.user1@example.com", \
        f"Email was not sanitized correctly on create. Expected 'test.user1@example.com', got: '{create_data.get('email')}'"
    
    created_user_id = create_data.get("id")
    assert created_user_id is not None, "Failed to get created user ID from response"

    # Step 2: Update User with Unsanitized Email
    update_url = f"http://localhost:{PORT}/api/collections/users/records/{created_user_id}"
    update_payload = {
        "email": "  NEW.EMAIL@example.com"
    }
    
    update_response = requests.patch(update_url, json=update_payload)
    assert update_response.status_code == 200, f"Failed to update user: {update_response.text}"
    
    update_data = update_response.json()
    assert update_data.get("email") == "new.email@example.com", \
        f"Email was not sanitized correctly on update. Expected 'new.email@example.com', got: '{update_data.get('email')}'"
