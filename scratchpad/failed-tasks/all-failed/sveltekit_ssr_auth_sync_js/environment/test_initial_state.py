import os
import shutil
import subprocess
import time
import requests
import pytest

PROJECT_DIR = "/home/user/sveltekit-app"

def test_node_and_npm_available():
    assert shutil.which("node") is not None, "node binary not found in PATH."
    assert shutil.which("npm") is not None, "npm binary not found in PATH."

def test_pocketbase_available():
    assert shutil.which("pocketbase") is not None, "pocketbase binary not found in PATH."

def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} does not exist."

def test_pocketbase_running_and_test_user_exists():
    # Check if PocketBase is already running, if not start it
    try:
        requests.get("http://127.0.0.1:8090/api/health", timeout=1)
    except requests.exceptions.ConnectionError:
        subprocess.Popen(
            ["pocketbase", "serve", "--http=127.0.0.1:8090", "--dir=/home/user/pb_data"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(2)
        
    # Verify it's running
    try:
        resp = requests.get("http://127.0.0.1:8090/api/health", timeout=2)
        assert resp.status_code == 200, "PocketBase health check failed."
    except requests.exceptions.ConnectionError:
        pytest.fail("PocketBase is not running on port 8090.")
        
    # Try to authenticate to see if the user exists
    auth_resp = requests.post("http://127.0.0.1:8090/api/collections/users/auth-with-password", json={
        "identity": "test@example.com",
        "password": "password123"
    })
    
    if auth_resp.status_code != 200:
        # Create the user
        user_data = {
            "email": "test@example.com",
            "password": "password123",
            "passwordConfirm": "password123"
        }
        create_resp = requests.post("http://127.0.0.1:8090/api/collections/users/records", json=user_data)
        assert create_resp.status_code == 200, f"Failed to create test user: {create_resp.text}"
