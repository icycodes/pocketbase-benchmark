import os
import shutil
import pytest
import requests
import socket
from xprocess import ProcessStarter

PROJECT_DIR = "/home/user/myproject"

@pytest.fixture(scope="session")
def start_app(xprocess):
    # Setup: Clean up existing data to ensure a fresh start
    pb_data_dir = os.path.join(PROJECT_DIR, "pb_data")
    if os.path.isdir(pb_data_dir):
        shutil.rmtree(pb_data_dir)
        
    class Starter(ProcessStarter):
        name = "start_app"
        args = ["./server", "serve", "--http=0.0.0.0:8090"]
        env = os.environ.copy()
        popen_kwargs = {
            "cwd": PROJECT_DIR,
            "text": True,
        }
        timeout = 30
        terminate_on_interrupt = True

        def startup_check(self):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(("127.0.0.1", 8090)) == 0

    xprocess.ensure(Starter.name, Starter)

    yield

    info = xprocess.getinfo(Starter.name)
    info.terminate()

def test_hook_with_empty_title(start_app):
    url = "http://127.0.0.1:8090/api/collections/posts/records"
    payload = {"content": "Test content without title"}
    response = requests.post(url, json=payload)
    
    assert response.status_code == 400, f"Expected status 400 for empty title, got {response.status_code}. Response: {response.text}"
    assert "Title cannot be empty" in response.text, f"Expected error message 'Title cannot be empty' not found in response: {response.text}"

def test_hook_with_valid_title(start_app):
    url = "http://127.0.0.1:8090/api/collections/posts/records"
    payload = {"title": "My Awesome Post", "content": "This is a test post."}
    response = requests.post(url, json=payload)
    
    assert response.status_code == 200, f"Expected status 200 for valid title, got {response.status_code}. Response: {response.text}"
    
    data = response.json()
    assert data.get("title") == "My Awesome Post", f"Expected title 'My Awesome Post', got {data.get('title')}"
    assert data.get("slug") == "my-awesome-post", f"Expected slug 'my-awesome-post', got {data.get('slug')}"
