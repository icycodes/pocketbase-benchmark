import os
import socket
import pytest
import requests
import subprocess
from xprocess import ProcessStarter

PROJECT_DIR = "/home/user/myproject"

@pytest.fixture(scope="session")
def start_app(xprocess):
    # Compile the Go application
    compile_result = subprocess.run(
        ["go", "build", "-o", "myapp", "main.go"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True
    )
    if compile_result.returncode != 0:
        pytest.fail(f"Failed to compile application: {compile_result.stderr}")

    class Starter(ProcessStarter):
        name = "pocketbase_app"
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

def test_create_post_success(start_app):
    url = "http://localhost:8090/api/collections/posts/records"
    payload = {"title": "My First Post"}
    response = requests.post(url, json=payload)
    
    assert response.status_code == 200, f"Expected status 200, got {response.status_code}. Response: {response.text}"
    
    data = response.json()
    assert data.get("title") == "My First Post", f"Expected title 'My First Post', got: {data.get('title')}"
    assert data.get("slug") == "my-first-post", f"Expected slug 'my-first-post', got: {data.get('slug')}"

def test_create_post_validation_error(start_app):
    url = "http://localhost:8090/api/collections/posts/records"
    payload = {"title": ""}
    response = requests.post(url, json=payload)
    
    assert response.status_code == 400, f"Expected status 400 for empty title, got {response.status_code}. Response: {response.text}"
