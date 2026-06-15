import os
import pytest
import requests
import socket
from xprocess import ProcessStarter

PROJECT_DIR = "/home/user/myproject"

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

def test_create_post_with_valid_title(start_app):
    url = "http://localhost:8090/api/collections/posts/records"
    payload = {"title": "Hello PocketBase World"}
    response = requests.post(url, json=payload)
    
    assert response.status_code == 200, f"Expected status 200, got {response.status_code}. Response: {response.text}"
    
    data = response.json()
    assert data.get("title") == "Hello PocketBase World", "Title does not match the input."
    assert data.get("slug") == "hello-pocketbase-world", f"Expected slug 'hello-pocketbase-world', got '{data.get('slug')}'"

def test_create_post_with_special_characters(start_app):
    url = "http://localhost:8090/api/collections/posts/records"
    payload = {"title": "Test @ 123!"}
    response = requests.post(url, json=payload)
    
    assert response.status_code == 200, f"Expected status 200, got {response.status_code}. Response: {response.text}"
    
    data = response.json()
    assert data.get("title") == "Test @ 123!", "Title does not match the input."
    # PocketBase slugify implementation converts "Test @ 123!" to "test-123"
    assert data.get("slug") == "test-123", f"Expected slug 'test-123', got '{data.get('slug')}'"

def test_create_post_without_title(start_app):
    url = "http://localhost:8090/api/collections/posts/records"
    payload = {"content": "This has no title"}
    response = requests.post(url, json=payload)
    
    assert response.status_code == 400, f"Expected status 400 for missing title, got {response.status_code}. Response: {response.text}"
