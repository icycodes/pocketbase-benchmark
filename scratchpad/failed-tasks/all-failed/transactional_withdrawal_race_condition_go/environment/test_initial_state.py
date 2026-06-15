import os
import shutil

def test_go_binary_available():
    assert shutil.which("go") is not None, "go binary not found in PATH."

def test_project_dir_exists():
    assert os.path.isdir("/home/user/app"), "Project directory /home/user/app does not exist."

def test_main_go_exists():
    assert os.path.isfile("/home/user/app/main.go"), "main.go does not exist in /home/user/app."

def test_go_mod_exists():
    assert os.path.isfile("/home/user/app/go.mod"), "go.mod does not exist in /home/user/app."