import os
import shutil
import pytest

PROJECT_DIR = "/home/user/app"

def test_go_binary_available():
    assert shutil.which("go") is not None, "go binary not found in PATH."

def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} does not exist."

def test_main_go_exists():
    main_go_path = os.path.join(PROJECT_DIR, "main.go")
    assert os.path.isfile(main_go_path), f"main.go file {main_go_path} does not exist."

def test_go_mod_exists():
    go_mod_path = os.path.join(PROJECT_DIR, "go.mod")
    assert os.path.isfile(go_mod_path), f"go.mod file {go_mod_path} does not exist."
