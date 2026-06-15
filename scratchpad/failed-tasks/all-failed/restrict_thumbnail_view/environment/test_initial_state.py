import os
import pytest

PROJECT_DIR = "/home/user/pb"

def test_project_dir_exists():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} does not exist."

def test_pocketbase_binary_exists():
    pb_path = os.path.join(PROJECT_DIR, "pocketbase")
    assert os.path.isfile(pb_path), f"PocketBase binary {pb_path} does not exist."
    assert os.access(pb_path, os.X_OK), f"PocketBase binary {pb_path} is not executable."

def test_pb_data_exists():
    pb_data_path = os.path.join(PROJECT_DIR, "pb_data")
    assert os.path.isdir(pb_data_path), f"PocketBase data directory {pb_data_path} does not exist. The initial state should have a pre-configured database."