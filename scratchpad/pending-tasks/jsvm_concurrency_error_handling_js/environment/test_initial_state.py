import os
import subprocess
import time
import urllib.request
import pytest

PROJECT_DIR = "/home/user/pocketbase_app"

def test_project_dir_exists():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} does not exist."

def test_pocketbase_binary_exists():
    pb_path = os.path.join(PROJECT_DIR, "pocketbase")
    assert os.path.isfile(pb_path), f"PocketBase binary not found at {pb_path}."
    assert os.access(pb_path, os.X_OK), f"PocketBase binary at {pb_path} is not executable."

def test_mock_webhook_script_exists():
    script_path = os.path.join(PROJECT_DIR, "mock_webhook.py")
    assert os.path.isfile(script_path), f"Mock webhook script not found at {script_path}."

def test_start_mock_webhook_server():
    # Start the mock webhook server in the background
    script_path = os.path.join(PROJECT_DIR, "mock_webhook.py")
    
    # Check if it's already running on port 8081
    try:
        urllib.request.urlopen("http://127.0.0.1:8081/", timeout=1)
        # Already running
        return
    except Exception:
        pass

    subprocess.Popen(["python3", script_path], cwd=PROJECT_DIR)
    
    # Wait for the server to start
    max_retries = 10
    for _ in range(max_retries):
        try:
            urllib.request.urlopen("http://127.0.0.1:8081/", timeout=1)
            break
        except Exception:
            time.sleep(0.5)
    else:
        pytest.fail("Mock webhook server failed to start on port 8081.")
