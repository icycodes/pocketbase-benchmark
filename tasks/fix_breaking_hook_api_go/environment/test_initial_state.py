import os
import shutil
import pytest

PROJECT_DIR = "/home/user/myproject"

def test_go_binary_available():
    assert shutil.which("go") is not None, "go binary not found in PATH."

def test_project_dir_exists():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} does not exist."

def test_go_mod_exists():
    go_mod_path = os.path.join(PROJECT_DIR, "go.mod")
    assert os.path.isfile(go_mod_path), f"go.mod file {go_mod_path} does not exist."
    with open(go_mod_path, "r") as f:
        content = f.read()
    assert "github.com/pocketbase/pocketbase" in content, "go.mod does not contain pocketbase dependency."

def test_main_go_exists_and_has_broken_syntax():
    main_go_path = os.path.join(PROJECT_DIR, "main.go")
    assert os.path.isfile(main_go_path), f"main.go file {main_go_path} does not exist."
    
    with open(main_go_path, "r") as f:
        content = f.read()
    
    # Assert it has the old .Add() syntax
    assert ".Add(" in content, "main.go should contain the broken v0.22 .Add() hook registration syntax."
    assert "core.RecordRequestEvent" not in content, "main.go should not yet contain the new v0.23+ event type."
