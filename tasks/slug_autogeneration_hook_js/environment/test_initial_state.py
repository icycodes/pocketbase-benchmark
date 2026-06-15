import os
import shutil

PROJECT_DIR = "/home/user/pocketbase_app"

def test_project_dir_exists():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} does not exist."

def test_pocketbase_binary_exists():
    binary_path = os.path.join(PROJECT_DIR, "pocketbase")
    assert os.path.isfile(binary_path), f"PocketBase binary not found at {binary_path}."
    assert os.access(binary_path, os.X_OK), f"PocketBase binary at {binary_path} is not executable."

def test_pb_hooks_dir_exists():
    hooks_dir = os.path.join(PROJECT_DIR, "pb_hooks")
    assert os.path.isdir(hooks_dir), f"pb_hooks directory not found at {hooks_dir}."
