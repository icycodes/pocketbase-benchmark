import os
import subprocess

PROJECT_DIR = "/home/user/pocketbase_app"
PB_BINARY = os.path.join(PROJECT_DIR, "pocketbase")

def test_pocketbase_binary_available():
    assert os.path.isfile(PB_BINARY), f"PocketBase binary not found at {PB_BINARY}."
    assert os.access(PB_BINARY, os.X_OK), f"PocketBase binary at {PB_BINARY} is not executable."

def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} does not exist."

def test_pb_hooks_directory_exists():
    hooks_dir = os.path.join(PROJECT_DIR, "pb_hooks")
    assert os.path.isdir(hooks_dir), f"Hooks directory {hooks_dir} does not exist."

def test_database_exists():
    db_path = os.path.join(PROJECT_DIR, "pb_data", "data.db")
    assert os.path.isfile(db_path), f"Database file {db_path} does not exist. The schema should be pre-initialized."
