import os
import subprocess
import socket
import pytest
import requests
from xprocess import ProcessStarter

PROJECT_DIR = "/home/user/sveltekit-app"

@pytest.fixture(scope="session")
def start_pocketbase(xprocess):
    class Starter(ProcessStarter):
        name = "pocketbase"
        args = ["pocketbase", "serve", "--http=127.0.0.1:8090", "--dir=/home/user/pb_data"]
        env = os.environ.copy()
        popen_kwargs = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
        timeout = 30
        terminate_on_interrupt = True

        def startup_check(self):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(("127.0.0.1", 8090)) == 0

    xprocess.ensure(Starter.name, Starter)
    yield
    info = xprocess.getinfo(Starter.name)
    info.terminate()

@pytest.fixture(scope="session")
def start_sveltekit(xprocess, start_pocketbase):
    # Run npm install first
    subprocess.run(["npm", "install"], cwd=PROJECT_DIR, check=True)

    class Starter(ProcessStarter):
        name = "sveltekit"
        args = ["npm", "run", "dev"]
        env = os.environ.copy()
        popen_kwargs = {
            "cwd": PROJECT_DIR,
            "text": True,
        }
        timeout = 60
        terminate_on_interrupt = True

        def startup_check(self):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(("127.0.0.1", 5173)) == 0

    xprocess.ensure(Starter.name, Starter)
    yield
    info = xprocess.getinfo(Starter.name)
    info.terminate()

def test_unauthorized_access(start_sveltekit):
    """Verify that accessing /api/me without a cookie returns 401."""
    resp = requests.get("http://localhost:5173/api/me")
    assert resp.status_code == 401, f"Expected 401 for unauthorized access, got {resp.status_code}"

def test_login_and_authorized_access(start_sveltekit):
    """Verify that login returns a pb_auth cookie and allows access to /api/me."""
    # Step 1: Login
    login_payload = {
        "email": "test@example.com",
        "password": "password123"
    }
    login_resp = requests.post("http://localhost:5173/api/login", json=login_payload)
    assert login_resp.status_code == 200, f"Expected 200 for login, got {login_resp.status_code}. Response: {login_resp.text}"
    
    # Check for set-cookie header containing pb_auth
    set_cookie = login_resp.headers.get("set-cookie")
    assert set_cookie is not None, "Expected set-cookie header in login response"
    assert "pb_auth=" in set_cookie, f"Expected pb_auth cookie in set-cookie header, got: {set_cookie}"
    
    # Extract the cookie string to send in the next request
    # requests handles cookies automatically if using a Session, but we can also pass it manually
    cookies = {"pb_auth": login_resp.cookies.get("pb_auth")}
    
    # Step 2: Access protected route
    me_resp = requests.get("http://localhost:5173/api/me", cookies=cookies)
    assert me_resp.status_code == 200, f"Expected 200 for authorized access, got {me_resp.status_code}. Response: {me_resp.text}"
    
    data = me_resp.json()
    assert data.get("email") == "test@example.com", f"Expected email to be test@example.com, got {data.get('email')}"
