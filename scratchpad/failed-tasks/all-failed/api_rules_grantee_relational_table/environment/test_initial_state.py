import os
import pytest

PROJECT_DIR = "/home/user/myproject"
PB_BINARY = os.path.join(PROJECT_DIR, "pocketbase")

def test_project_dir_exists():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} does not exist."

def test_pocketbase_binary_exists():
    assert os.path.isfile(PB_BINARY), f"PocketBase binary not found at {PB_BINARY}."
    assert os.access(PB_BINARY, os.X_OK), f"PocketBase binary at {PB_BINARY} is not executable."
