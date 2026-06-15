import os
import shutil
import pytest

PROJECT_DIR = "/home/user/myproject"

def test_node_available():
    assert shutil.which("node") is not None, "node binary not found in PATH."

def test_npm_available():
    assert shutil.which("npm") is not None, "npm binary not found in PATH."

def test_pocketbase_binary_available():
    assert os.path.exists("/usr/local/bin/pocketbase"), "pocketbase binary not found at /usr/local/bin/pocketbase."

def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} does not exist."

def test_package_json_exists():
    package_json_path = os.path.join(PROJECT_DIR, "package.json")
    assert os.path.isfile(package_json_path), f"package.json does not exist at {package_json_path}."
