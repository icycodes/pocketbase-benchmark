import os
import shutil

PROJECT_DIR = "/home/user/myproject"

def test_go_binary_available():
    assert shutil.which("go") is not None, "Go binary not found in PATH."

def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} does not exist."
