import os
import subprocess
import time
import socket
import requests
import urllib.parse
import json
import pytest
from xprocess import ProcessStarter

PROJECT_DIR = "/home/user/sveltekit-app"
PB_DIR = "/home/user/pb"

@pytest.fixture(scope="session")
def start_pocketbase(xprocess):
    class Starter(ProcessStarter):
        name = "pocketbase_server"
        args = ["pocketbase", "serve", "--http=0.0.0.0:8090", "--dir=" + PB_DIR + "/pb_data", "--publicDir=" + PB_DIR + "/pb_public"]
        env = os.environ.copy()
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
    class Starter(ProcessStarter):
        name = "sveltekit_server"
        args = ["npm", "run", "dev", "--", "--port", "5173"]
        env = os.environ.copy()
        popen_kwargs = {
            "cwd": PROJECT_DIR,
            "text": True,
        }
        timeout = 180
        terminate_on_interrupt = True

        def startup_check(self):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(("127.0.0.1", 5173)) == 0

    xprocess.ensure(Starter.name, Starter)
    yield
    info = xprocess.getinfo(Starter.name)
    info.terminate()

def test_valid_token_refresh(start_sveltekit):
    # 1. Create a test user in PocketBase
    create_url = "http://127.0.0.1:8090/api/collections/users/records"
    user_data = {
        "email": "test_user_refresh@example.com",
        "password": "password123",
        "passwordConfirm": "password123"
    }
    # ignore errors if already exists
    requests.post(create_url, json=user_data)
    
    # Authenticate to get valid token
    auth_url = "http://127.0.0.1:8090/api/collections/users/auth-with-password"
    auth_resp = requests.post(auth_url, json={"identity": "test_user_refresh@example.com", "password": "password123"})
    assert auth_resp.status_code == 200, f"Failed to authenticate test user: {auth_resp.text}"
    
    auth_data = auth_resp.json()
    token = auth_data.get("token")
    model = auth_data.get("record")
    
    assert token, "No token returned from PocketBase"
    
    # Construct pb_auth cookie
    cookie_obj = {
        "token": token,
        "model": model
    }
    cookie_str = urllib.parse.quote(json.dumps(cookie_obj))
    pb_auth_cookie = f"pb_auth={cookie_str}"
    
    # Request to SvelteKit
    svelte_url = "http://127.0.0.1:5173/"
    headers = {"Cookie": pb_auth_cookie}
    svelte_resp = requests.get(svelte_url, headers=headers)
    
    # Check set-cookie header
    set_cookie = svelte_resp.headers.get("set-cookie", "")
    assert "pb_auth=" in set_cookie, "Response missing 'pb_auth' in set-cookie header"
    
    # The new token should be different or at least present
    # We can just parse the new cookie to see if it's valid
    assert "token" in urllib.parse.unquote(set_cookie), "New pb_auth cookie does not contain token"

def test_invalid_token_clearing(start_sveltekit):
    # Construct invalid pb_auth cookie
    cookie_obj = {
        "token": "invalid.jwt.token",
        "model": None
    }
    cookie_str = urllib.parse.quote(json.dumps(cookie_obj))
    pb_auth_cookie = f"pb_auth={cookie_str}"
    
    # Request to SvelteKit
    svelte_url = "http://127.0.0.1:5173/"
    headers = {"Cookie": pb_auth_cookie}
    svelte_resp = requests.get(svelte_url, headers=headers)
    
    # Check set-cookie header
    set_cookie = svelte_resp.headers.get("set-cookie", "")
    
    # It should clear the cookie
    assert "pb_auth=" in set_cookie, "Response missing 'pb_auth' in set-cookie header"
    # Usually cleared by setting empty value or past expiration
    assert "pb_auth=;" in set_cookie or "Expires=" in set_cookie or "Max-Age=0" in set_cookie, \
        f"Cookie not cleared properly. set-cookie header: {set_cookie}"
