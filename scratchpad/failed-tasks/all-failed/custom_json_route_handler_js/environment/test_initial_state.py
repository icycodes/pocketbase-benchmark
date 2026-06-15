import os
import shutil

PROJECT_DIR = "/home/user/myproject"

def test_project_dir_exists():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} does not exist."

def test_pocketbase_binary_exists():
    pb_path = os.path.join(PROJECT_DIR, "pocketbase")
    assert os.path.isfile(pb_path), "pocketbase binary not found in project directory."
    assert os.access(pb_path, os.X_OK), "pocketbase binary is not executable."

def test_pb_hooks_dir_exists():
    hooks_dir = os.path.join(PROJECT_DIR, "pb_hooks")
    assert os.path.isdir(hooks_dir), f"pb_hooks directory {hooks_dir} does not exist."
