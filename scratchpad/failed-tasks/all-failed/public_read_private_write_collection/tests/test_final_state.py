import os
import pytest
import requests
import socket
from xprocess import ProcessStarter

PROJECT_DIR = "/home/user/pb-app"
BASE_URL = "http://127.0.0.1:8090"

@pytest.fixture(scope="session")
def start_app(xprocess):
    class Starter(ProcessStarter):
        name = "pb_app"
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
                return s.connect_ex(("127.0.0.1", 8090)) == 0

    xprocess.ensure(Starter.name, Starter)
    yield
    info = xprocess.getinfo(Starter.name)
    info.terminate()

def get_run_id():
    run_id = os.environ.get("ZEALT_RUN_ID", "default")
    return run_id

def test_public_read(start_app):
    run_id = get_run_id()
    url = f"{BASE_URL}/api/collections/contacts_{run_id}/records"
    response = requests.get(url)
    assert response.status_code == 200, f"Expected 200 OK for public read, got {response.status_code}. Response: {response.text}"

def test_guest_write_fails(start_app):
    run_id = get_run_id()
    url = f"{BASE_URL}/api/collections/contacts_{run_id}/records"
    data = {"name": "Guest", "email": "guest@example.com"}
    response = requests.post(url, json=data)
    # PocketBase typically returns 400 or 403 for unauthorized/failed API rules
    assert response.status_code in [400, 401, 403], f"Expected error status for guest write, got {response.status_code}. Response: {response.text}"

def test_authenticated_write(start_app):
    run_id = get_run_id()
    
    # 1. Create a user
    users_url = f"{BASE_URL}/api/collections/users/records"
    user_email = f"testuser_{run_id}@example.com"
    user_password = "password123"
    
    create_user_data = {
        "email": user_email,
        "password": user_password,
        "passwordConfirm": user_password
    }
    create_response = requests.post(users_url, json=create_user_data)
    assert create_response.status_code == 200, f"Failed to create test user: {create_response.text}"
    
    # 2. Authenticate the user
    auth_url = f"{BASE_URL}/api/collections/users/auth-with-password"
    auth_data = {
        "identity": user_email,
        "password": user_password
    }
    auth_response = requests.post(auth_url, json=auth_data)
    assert auth_response.status_code == 200, f"Failed to authenticate user: {auth_response.text}"
    
    token = auth_response.json().get("token")
    assert token, "No token found in auth response"
    
    # 3. Authenticated write
    contacts_url = f"{BASE_URL}/api/collections/contacts_{run_id}/records"
    contact_data = {
        "name": "Auth User",
        "email": "auth@example.com"
    }
    headers = {
        "Authorization": token
    }
    write_response = requests.post(contacts_url, json=contact_data, headers=headers)
    assert write_response.status_code == 200, f"Expected 200 OK for authenticated write, got {write_response.status_code}. Response: {write_response.text}"
    
    # Verify the record was created
    record = write_response.json()
    assert "id" in record, "Record ID not found in response"
    assert record.get("name") == "Auth User", f"Expected name 'Auth User', got {record.get('name')}"
    assert record.get("email") == "auth@example.com", f"Expected email 'auth@example.com', got {record.get('email')}"
