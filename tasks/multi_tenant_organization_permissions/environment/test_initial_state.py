import os
import pytest

PROJECT_DIR = "/home/user/myproject"

def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} does not exist."

def test_pocketbase_binary_exists():
    pb_path = os.path.join(PROJECT_DIR, "pocketbase")
    assert os.path.isfile(pb_path), f"PocketBase binary {pb_path} does not exist."
    assert os.access(pb_path, os.X_OK), f"PocketBase binary {pb_path} is not executable."
