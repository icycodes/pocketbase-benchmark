import os
import pytest
import stat

PROJECT_DIR = "/home/user/myproject"

def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} does not exist."

def test_pocketbase_binary_exists():
    pb_path = os.path.join(PROJECT_DIR, "pocketbase")
    assert os.path.isfile(pb_path), f"PocketBase binary not found at {pb_path}."
    assert os.stat(pb_path).st_mode & stat.S_IXUSR, f"PocketBase binary at {pb_path} is not executable."
