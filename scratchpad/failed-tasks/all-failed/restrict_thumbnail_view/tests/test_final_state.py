import os
import socket
import pytest
import requests
from xprocess import ProcessStarter
import tempfile

PROJECT_DIR = "/home/user/pb"
BASE_URL = "http://localhost:8090"

@pytest.fixture(scope="session")
def start_app(xprocess):
    class Starter(ProcessStarter):
        name = "pocketbase"
        args = ["./pocketbase", "serve", "--http=0.0.0.0:8090"]
        env = os.environ.copy()
        popen_kwargs = {
            "cwd": PROJECT_DIR,
            "text": True,
        }
        timeout = 10
        terminate_on_interrupt = True

        def startup_check(self):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(("localhost", 8090)) == 0

    xprocess.ensure(Starter.name, Starter)
    yield
    info = xprocess.getinfo(Starter.name)
    info.terminate()

def test_thumbnail_access_rules(start_app):
    # 1. Setup Test Data
    # Create test user
    email = "testuser@example.com"
    password = "password123"
    
    # Check if user already exists
    users_resp = requests.get(f"{BASE_URL}/api/collections/users/records", params={"filter": f"email='{email}'"})
    if users_resp.status_code == 200 and users_resp.json().get("totalItems", 0) > 0:
        user_id = users_resp.json()["items"][0]["id"]
        requests.patch(f"{BASE_URL}/api/collections/users/records/{user_id}", json={"password": password, "passwordConfirm": password})
    else:
        create_user_resp = requests.post(
            f"{BASE_URL}/api/collections/users/records",
            json={
                "email": email,
                "password": password,
                "passwordConfirm": password
            }
        )
        assert create_user_resp.status_code in [200, 201], f"Failed to create test user: {create_user_resp.text}"

    # Authenticate user
    auth_resp = requests.post(
        f"{BASE_URL}/api/collections/users/auth-with-password",
        json={
            "identity": email,
            "password": password
        }
    )
    assert auth_resp.status_code == 200, f"Failed to authenticate: {auth_resp.text}"
    token = auth_resp.json()["token"]

    # Create a dummy image file
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_img:
        # 1x1 transparent PNG
        img_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        tmp_img.write(img_data)
        tmp_img.flush()
        tmp_img_path = tmp_img.name

    try:
        # Create a record in posts collection
        with open(tmp_img_path, "rb") as f:
            create_post_resp = requests.post(
                f"{BASE_URL}/api/collections/posts/records",
                headers={"Authorization": token},
                files={"image": ("test.png", f, "image/png")}
            )
        assert create_post_resp.status_code in [200, 201], f"Failed to create post record. Make sure the posts collection exists and the user has permission to create records: {create_post_resp.text}"
        
        post_record = create_post_resp.json()
        record_id = post_record["id"]
        filename = post_record["image"]
        
        thumb_url = f"{BASE_URL}/api/files/posts/{record_id}/{filename}?thumb=100x100"
        
        # 2. Test Unauthenticated Access
        unauth_resp = requests.get(thumb_url)
        assert unauth_resp.status_code != 200, f"Unauthenticated request should not succeed, but got status {unauth_resp.status_code}"
        assert unauth_resp.status_code in [401, 403, 404], f"Expected 401, 403, or 404 for protected file without auth, got {unauth_resp.status_code}"

        # 3. Test Authenticated Access
        auth_req_resp = requests.get(thumb_url, headers={"Authorization": token})
        assert auth_req_resp.status_code == 200, f"Authenticated request failed: {auth_req_resp.text}"
        assert len(auth_req_resp.content) > 0, "Response content is empty"
    finally:
        os.remove(tmp_img_path)
