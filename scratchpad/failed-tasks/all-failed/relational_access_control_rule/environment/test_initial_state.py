import os
import shutil

PROJECT_DIR = "/home/user/myproject"

def test_project_dir_exists():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} does not exist."

def test_pocketbase_binary_exists():
    pb_path = os.path.join(PROJECT_DIR, "pocketbase")
    assert os.path.isfile(pb_path), f"PocketBase binary not found at {pb_path}."
    assert os.access(pb_path, os.X_OK), f"PocketBase binary at {pb_path} is not executable."

def test_pb_migrations_dir_exists():
    migrations_dir = os.path.join(PROJECT_DIR, "pb_migrations")
    assert os.path.isdir(migrations_dir), f"pb_migrations directory not found at {migrations_dir}."
