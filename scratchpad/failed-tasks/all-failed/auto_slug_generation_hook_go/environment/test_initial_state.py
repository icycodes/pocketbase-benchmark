import os
import shutil

PROJECT_DIR = "/home/user/myproject"

def test_go_available():
    assert shutil.which("go") is not None, "go binary not found in PATH."

def test_project_dir_exists():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} does not exist."

def test_pb_data_exists():
    pb_data_dir = os.path.join(PROJECT_DIR, "pb_data")
    assert os.path.isdir(pb_data_dir), f"PocketBase data directory {pb_data_dir} does not exist."
    
    # Check if data.db exists
    db_file = os.path.join(pb_data_dir, "data.db")
    assert os.path.isfile(db_file), f"Database file {db_file} does not exist."
