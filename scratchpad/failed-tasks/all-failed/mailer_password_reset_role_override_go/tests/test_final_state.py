import os
import subprocess
import socket
import json
import time
import requests
import pytest
from xprocess import ProcessStarter

PROJECT_DIR = "/home/user/app"

@pytest.fixture(scope="session", autouse=True)
def setup_sendmail():
    """Create a mock sendmail script to capture emails."""
    sendmail_path = "/usr/sbin/sendmail"
    script_content = "#!/bin/bash\ncat > /tmp/last_email.txt\n"
    
    # We might need sudo if not root, but tests usually run as root or we can just write to a local fake sendmail and put it in PATH
    # Since we don't know if we are root, let's just write it to /tmp/fake_sendmail and prepend /tmp to PATH
    fake_sendmail = "/tmp/sendmail"
    with open(fake_sendmail, "w") as f:
        f.write(script_content)
    os.chmod(fake_sendmail, 0o755)
    
    # Also try to write to /usr/sbin/sendmail if possible
    try:
        with open(sendmail_path, "w") as f:
            f.write(script_content)
        os.chmod(sendmail_path, 0o755)
    except Exception:
        pass
        
    yield

@pytest.fixture(scope="session")
def start_app(xprocess):
    # Build the app
    build_result = subprocess.run(
        ["go", "build", "-o", "pb", "main.go"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True
    )
    assert build_result.returncode == 0, f"go build failed: {build_result.stderr}"

    class Starter(ProcessStarter):
        name = "pb_app"
        args = ["./pb", "serve", "--http", "0.0.0.0:8090"]
        env = os.environ.copy()
        # Prepend /tmp to PATH so our fake sendmail is found first if not in /usr/sbin
        env["PATH"] = "/tmp:" + env.get("PATH", "")
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

@pytest.fixture(scope="session")
def setup_users(start_app):
    """Setup admin user, ensure role field exists, and create test users."""
    base_url = "http://localhost:8090"
    
    # 1. Create an admin
    admin_email = "super@example.com"
    admin_password = "password123456"
    
    # We can use the CLI to create a superuser
    subprocess.run(
        ["./pb", "superuser", "upsert", admin_email, admin_password],
        cwd=PROJECT_DIR,
        check=True
    )
    
    # 2. Authenticate as admin
    resp = requests.post(f"{base_url}/api/collections/_superusers/auth-with-password", json={
        "identity": admin_email,
        "password": admin_password
    })
    assert resp.status_code == 200, "Failed to authenticate admin"
    token = resp.json()["token"]
    headers = {"Authorization": token}
    
    # 3. Ensure 'role' field exists in 'users' collection
    resp = requests.get(f"{base_url}/api/collections/users", headers=headers)
    assert resp.status_code == 200
    collection = resp.json()
    
    fields = collection.get("fields", [])
    has_role = any(f.get("name") == "role" for f in fields)
    
    if not has_role:
        fields.append({
            "name": "role",
            "type": "text",
            "required": False,
            "options": {"min": None, "max": None, "pattern": ""}
        })
        resp = requests.patch(f"{base_url}/api/collections/users", json={"fields": fields}, headers=headers)
        assert resp.status_code == 200, "Failed to add role field to users collection"
        
    # 4. Create test users
    # Delete existing if any
    for email in ["admin_test@example.com", "user_test@example.com"]:
        resp = requests.get(f"{base_url}/api/collections/users/records", params={"filter": f"email='{email}'"}, headers=headers)
        if resp.status_code == 200 and resp.json().get("items"):
            for item in resp.json()["items"]:
                requests.delete(f"{base_url}/api/collections/users/records/{item['id']}", headers=headers)
                
    users = [
        {"email": "admin_test@example.com", "password": "password123", "passwordConfirm": "password123", "role": "admin"},
        {"email": "user_test@example.com", "password": "password123", "passwordConfirm": "password123", "role": "user"}
    ]
    
    for u in users:
        resp = requests.post(f"{base_url}/api/collections/users/records", json=u, headers=headers)
        assert resp.status_code == 200, f"Failed to create user {u['email']}: {resp.text}"
        
    return base_url

def test_admin_password_reset_email(setup_users):
    base_url = setup_users
    
    # Clear last email
    if os.path.exists("/tmp/last_email.txt"):
        os.remove("/tmp/last_email.txt")
        
    # Trigger password reset
    resp = requests.post(f"{base_url}/api/collections/users/request-password-reset", json={
        "email": "admin_test@example.com"
    })
    assert resp.status_code == 204, f"Failed to request password reset: {resp.text}"
    
    # Wait for email to be written
    time.sleep(1)
    
    assert os.path.exists("/tmp/last_email.txt"), "No email was sent (sendmail mock not triggered)"
    
    with open("/tmp/last_email.txt", "r") as f:
        email_content = f.read()
        
    assert "Subject: Admin Password Reset -" in email_content, f"Expected admin subject not found in email: {email_content}"
    assert "Admin Reset Link:" in email_content, f"Expected admin HTML body not found in email: {email_content}"

def test_user_password_reset_email(setup_users):
    base_url = setup_users
    
    # Clear last email
    if os.path.exists("/tmp/last_email.txt"):
        os.remove("/tmp/last_email.txt")
        
    # Trigger password reset
    resp = requests.post(f"{base_url}/api/collections/users/request-password-reset", json={
        "email": "user_test@example.com"
    })
    assert resp.status_code == 204, f"Failed to request password reset: {resp.text}"
    
    # Wait for email to be written
    time.sleep(1)
    
    assert os.path.exists("/tmp/last_email.txt"), "No email was sent (sendmail mock not triggered)"
    
    with open("/tmp/last_email.txt", "r") as f:
        email_content = f.read()
        
    assert "Subject: User Password Reset -" in email_content, f"Expected user subject not found in email: {email_content}"
    assert "User Reset Link:" in email_content, f"Expected user HTML body not found in email: {email_content}"
