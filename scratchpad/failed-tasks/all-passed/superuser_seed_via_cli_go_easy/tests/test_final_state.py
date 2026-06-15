import os
import subprocess
import requests
import pytest
import shutil
import time
import socket
from xprocess import ProcessStarter

PROJECT_DIR = "/home/user/pocketbase-app"

@pytest.fixture(scope="session", autouse=True)
def clean_pb_data():
    """Remove pb_data before tests."""
    pb_data = os.path.join(PROJECT_DIR, "pb_data")
    if os.path.exists(pb_data):
        shutil.rmtree(pb_data)
    yield

def test_create_superuser_via_cli():
    """Run the custom command to seed the superuser."""
    result = subprocess.run(
        ["go", "run", "main.go", "seed-superuser", "admin@example.com", "securepass123"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"Command failed: {result.stderr}"

def test_verify_superuser_creation(xprocess):
    """Verify we can authenticate with the created superuser."""
    class Starter(ProcessStarter):
        name = "pocketbase_app"
        args = ["go", "run", "main.go", "serve", "--http=127.0.0.1:8090"]
        env = os.environ.copy()
        popen_kwargs = {"cwd": PROJECT_DIR, "text": True}
        timeout = 60
        terminate_on_interrupt = True

        def startup_check(self):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(("127.0.0.1", 8090)) == 0

    xprocess.ensure(Starter.name, Starter)
    
    try:
        response = requests.post(
            "http://127.0.0.1:8090/api/collections/_superusers/auth-with-password",
            json={"identity": "admin@example.com", "password": "securepass123"}
        )
        assert response.status_code == 200, f"Failed to authenticate: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
    finally:
        info = xprocess.getinfo(Starter.name)
        info.terminate()

def test_upsert_superuser_via_cli():
    """Run the custom command again to update the password."""
    result = subprocess.run(
        ["go", "run", "main.go", "seed-superuser", "admin@example.com", "newpass456"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"Upsert command failed: {result.stderr}"

def test_verify_superuser_upsert(xprocess):
    """Verify we can authenticate with the new password."""
    class Starter(ProcessStarter):
        name = "pocketbase_app2"
        args = ["go", "run", "main.go", "serve", "--http=127.0.0.1:8090"]
        env = os.environ.copy()
        popen_kwargs = {"cwd": PROJECT_DIR, "text": True}
        timeout = 60
        terminate_on_interrupt = True

        def startup_check(self):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(("127.0.0.1", 8090)) == 0

    xprocess.ensure(Starter.name, Starter)
    
    try:
        response = requests.post(
            "http://127.0.0.1:8090/api/collections/_superusers/auth-with-password",
            json={"identity": "admin@example.com", "password": "newpass456"}
        )
        assert response.status_code == 200, f"Failed to authenticate with new password: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
    finally:
        info = xprocess.getinfo(Starter.name)
        info.terminate()
