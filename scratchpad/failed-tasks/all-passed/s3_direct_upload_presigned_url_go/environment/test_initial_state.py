import os
import shutil
import subprocess
import time
import urllib.request

PROJECT_DIR = "/home/user/app"

def test_go_binary_available():
    assert shutil.which("go") is not None, "go binary not found in PATH."

def test_project_dir_exists():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} does not exist."

def test_go_mod_exists():
    go_mod_path = os.path.join(PROJECT_DIR, "go.mod")
    assert os.path.isfile(go_mod_path), f"go.mod file {go_mod_path} does not exist."

def test_main_go_exists():
    main_go_path = os.path.join(PROJECT_DIR, "main.go")
    assert os.path.isfile(main_go_path), f"main.go file {main_go_path} does not exist."

def test_start_minio():
    # Start minio server in background
    env = os.environ.copy()
    env["MINIO_ROOT_USER"] = "minioadmin"
    env["MINIO_ROOT_PASSWORD"] = "minioadmin"
    
    # Check if minio binary is available
    assert shutil.which("minio") is not None, "minio binary not found in PATH."
    
    subprocess.Popen(
        ["minio", "server", "/data", "--address", ":9000"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # Wait for MinIO to be up
    success = False
    for _ in range(30):
        try:
            req = urllib.request.Request("http://127.0.0.1:9000/minio/health/live")
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    success = True
                    break
        except Exception:
            pass
        time.sleep(1)
    
    assert success, "MinIO failed to start"
