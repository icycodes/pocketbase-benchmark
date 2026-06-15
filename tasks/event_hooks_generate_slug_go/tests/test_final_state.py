import pytest
import os
import subprocess
import requests
import socket
import time
from xprocess import ProcessStarter

PROJECT_DIR = "/home/user/myproject"
APP_URL = "http://localhost:8090"

@pytest.fixture(scope="session")
def build_app():
    """Build the Go application before starting it."""
    result = subprocess.run(
        ["go", "build", "-o", "myapp"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"Failed to build the Go app: {result.stderr}"

@pytest.fixture(scope="session")
def start_app(build_app, xprocess):
    """
    Starts the PocketBase Go app using xprocess. Confirms readiness via port check.
    """
    class Starter(ProcessStarter):
        name = "start_app"
        args = ["./myapp", "serve", "--http=0.0.0.0:8090"]
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

def test_create_post_with_valid_title(start_app):
    """Test that creating a post with a valid title generates a slug."""
    response = requests.post(
        f"{APP_URL}/api/collections/posts/records",
        json={"title": "My First PocketBase Post"}
    )
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}. Response: {response.text}"
    
    data = response.json()
    assert data.get("title") == "My First PocketBase Post", f"Expected title 'My First PocketBase Post', got {data.get('title')}"
    assert data.get("slug") == "my-first-pocketbase-post", f"Expected slug 'my-first-pocketbase-post', got {data.get('slug')}"

def test_create_post_with_empty_title(start_app):
    """Test that creating a post with an empty title returns a 400 Bad Request."""
    response = requests.post(
        f"{APP_URL}/api/collections/posts/records",
        json={"title": ""}
    )
    assert response.status_code == 400, f"Expected status code 400, got {response.status_code}. Response: {response.text}"
    
    data = response.json()
    # PocketBase error responses typically contain a code and message.
    assert "code" in data or "message" in data, f"Expected an error response object, got {data}"

def test_create_post_without_title_field(start_app):
    """Test that creating a post without a title field returns a 400 Bad Request."""
    response = requests.post(
        f"{APP_URL}/api/collections/posts/records",
        json={}
    )
    assert response.status_code == 400, f"Expected status code 400, got {response.status_code}. Response: {response.text}"
    
    data = response.json()
    assert "code" in data or "message" in data, f"Expected an error response object, got {data}"
