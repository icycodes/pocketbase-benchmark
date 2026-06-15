import os
import shutil
import subprocess
import time
import urllib.request
import urllib.error

PROJECT_DIR = "/home/user/sveltekit-app"

def test_node_and_npm_available():
    assert shutil.which("node") is not None, "node binary not found in PATH."
    assert shutil.which("npm") is not None, "npm binary not found in PATH."

def test_pocketbase_binary_available():
    assert shutil.which("pocketbase") is not None, "pocketbase binary not found in PATH."

def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} does not exist."

def test_sveltekit_package_json_exists():
    package_json_path = os.path.join(PROJECT_DIR, "package.json")
    assert os.path.isfile(package_json_path), f"package.json not found in {PROJECT_DIR}."

def test_pocketbase_service_running():
    # Start PocketBase if not running
    try:
        urllib.request.urlopen("http://127.0.0.1:8090/api/health", timeout=2)
    except urllib.error.URLError:
        # Start PocketBase in the background
        pb_dir = "/home/user/pb"
        os.makedirs(pb_dir, exist_ok=True)
        subprocess.Popen(
            ["pocketbase", "serve", "--http=0.0.0.0:8090", "--dir=" + pb_dir + "/pb_data", "--publicDir=" + pb_dir + "/pb_public"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        # Wait for it to start
        time.sleep(2)
        
    # Check again
    try:
        resp = urllib.request.urlopen("http://127.0.0.1:8090/api/health", timeout=2)
        assert resp.status == 200, "PocketBase health endpoint returned non-200 status."
    except urllib.error.URLError as e:
        assert False, f"PocketBase is not running or not accessible on port 8090: {e}"
