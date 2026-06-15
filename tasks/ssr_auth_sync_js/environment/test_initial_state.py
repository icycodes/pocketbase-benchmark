import os
import shutil
import urllib.request
import urllib.error
import time
import subprocess

PROJECT_DIR = "/home/user/myproject"

def test_node_installed():
    assert shutil.which("node") is not None, "Node.js is not installed."
    assert shutil.which("npm") is not None, "npm is not installed."

def test_project_dir_exists():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} does not exist."

def test_package_json_exists():
    package_json_path = os.path.join(PROJECT_DIR, "package.json")
    assert os.path.isfile(package_json_path), f"package.json does not exist at {package_json_path}."

def test_pocketbase_running():
    # Check if PocketBase is already running
    url = "http://127.0.0.1:8090/api/health"
    try:
        response = urllib.request.urlopen(url, timeout=2)
        if response.status == 200:
            return
    except urllib.error.URLError:
        pass

    # Start PocketBase in the background
    pb_data_dir = "/home/user/pb_data"
    subprocess.Popen(
        ["pocketbase", "serve", "--http=127.0.0.1:8090", f"--dir={pb_data_dir}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True
    )

    # Wait for PocketBase to start
    max_retries = 10
    for i in range(max_retries):
        try:
            response = urllib.request.urlopen(url, timeout=2)
            if response.status == 200:
                return
        except urllib.error.URLError:
            pass
        time.sleep(1)
    assert False, "PocketBase is not running at http://127.0.0.1:8090"
