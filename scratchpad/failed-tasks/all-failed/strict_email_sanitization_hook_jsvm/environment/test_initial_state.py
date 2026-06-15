import os
import pytest

PROJECT_DIR = "/home/user/myproject"

def test_project_dir_exists():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} does not exist."

def test_pb_hooks_dir_exists():
    pb_hooks_dir = os.path.join(PROJECT_DIR, "pb_hooks")
    assert os.path.isdir(pb_hooks_dir), f"pb_hooks directory {pb_hooks_dir} does not exist."

def test_pocketbase_binary_exists():
    pb_bin = os.path.join(PROJECT_DIR, "pocketbase")
    assert os.path.isfile(pb_bin), f"PocketBase binary {pb_bin} does not exist."
    assert os.access(pb_bin, os.X_OK), f"PocketBase binary {pb_bin} is not executable."
