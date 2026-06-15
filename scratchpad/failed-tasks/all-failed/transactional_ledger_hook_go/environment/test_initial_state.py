import os
import shutil

PROJECT_DIR = "/home/user/myproject"

def test_go_binary_available():
    assert shutil.which("go") is not None, "go binary not found in PATH."

def test_project_dir_exists():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} does not exist."

def test_main_go_exists():
    main_go_path = os.path.join(PROJECT_DIR, "main.go")
    assert os.path.isfile(main_go_path), f"main.go file {main_go_path} does not exist."

def test_pb_data_exists():
    pb_data_path = os.path.join(PROJECT_DIR, "pb_data")
    assert os.path.isdir(pb_data_path), f"pb_data directory {pb_data_path} does not exist."
