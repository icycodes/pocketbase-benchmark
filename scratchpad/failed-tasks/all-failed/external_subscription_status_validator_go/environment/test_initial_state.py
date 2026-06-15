import os
import shutil
import pytest

PROJECT_DIR = "/home/user/myproject"
MOCK_SERVER_PATH = "/home/user/mock_server.py"

def test_go_binary_available():
    assert shutil.which("go") is not None, "go binary not found in PATH."

def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} does not exist."

def test_mock_server_script_exists():
    assert os.path.isfile(MOCK_SERVER_PATH), f"Mock server script {MOCK_SERVER_PATH} does not exist."
