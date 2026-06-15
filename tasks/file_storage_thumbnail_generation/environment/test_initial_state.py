import os
import shutil
import subprocess
import time
import urllib.request
import urllib.error
import json
import pytest

PROJECT_DIR = "/home/user/pb-task"

def test_node_available():
    assert shutil.which("node") is not None, "node binary not found in PATH."
    assert shutil.which("npm") is not None, "npm binary not found in PATH."

def test_project_dir_and_input_image_exist():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} does not exist."
    input_jpg = os.path.join(PROJECT_DIR, "input.jpg")
    assert os.path.isfile(input_jpg), f"Input image {input_jpg} does not exist."

def test_pocketbase_running_and_configured():
    assert shutil.which("pocketbase") is not None, "pocketbase binary not found in PATH."
    
    # Create superuser via CLI
    try:
        subprocess.run(["pocketbase", "superuser", "upsert", "admin@example.com", "adminpassword"], check=True)
    except subprocess.CalledProcessError as e:
        pytest.fail(f"Failed to create superuser: {e}")
        
    # Start pocketbase if not running
    try:
        urllib.request.urlopen("http://127.0.0.1:8090/api/health")
    except Exception:
        subprocess.Popen(["pocketbase", "serve", "--http=0.0.0.0:8090"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        time.sleep(2)
        
    # Check health
    try:
        resp = urllib.request.urlopen("http://127.0.0.1:8090/api/health")
        assert resp.status == 200
    except Exception as e:
        pytest.fail(f"PocketBase is not running: {e}")

    # Authenticate to get token
    req = urllib.request.Request("http://127.0.0.1:8090/api/collections/_superusers/auth-with-password", data=json.dumps({
        "identity": "admin@example.com",
        "password": "adminpassword"
    }).encode("utf-8"), headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req)
        auth_data = json.loads(resp.read().decode("utf-8"))
        token = auth_data["token"]
    except Exception as e:
        pytest.fail(f"Failed to authenticate admin: {e}")

    # Check if collection exists
    req = urllib.request.Request("http://127.0.0.1:8090/api/collections/gallery", headers={"Authorization": f"Bearer {token}"})
    try:
        urllib.request.urlopen(req)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            # Create collection
            collection_data = {
                "name": "gallery",
                "type": "base",
                "fields": [
                    {
                        "name": "image",
                        "type": "file",
                        "required": True,
                        "options": {
                            "maxSelect": 1,
                            "maxSize": 5242880,
                            "mimeTypes": ["image/jpeg", "image/png", "image/webp"],
                            "thumbs": ["100x100"]
                        }
                    }
                ]
            }
            req = urllib.request.Request("http://127.0.0.1:8090/api/collections", data=json.dumps(collection_data).encode("utf-8"), headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
            try:
                urllib.request.urlopen(req)
            except Exception as e2:
                pytest.fail(f"Failed to create collection: {e2}")
