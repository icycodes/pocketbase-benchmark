import os
import shutil

PROJECT_DIR = "/home/user/myproject"


def test_go_binary_available():
    assert shutil.which("go") is not None, "Go toolchain not found in PATH."


def test_project_dir_exists():
    assert os.path.isdir(PROJECT_DIR), f"Expected project directory {PROJECT_DIR} to exist."


def test_main_go_exists():
    main_path = os.path.join(PROJECT_DIR, "main.go")
    assert os.path.isfile(main_path), f"Expected {main_path} to exist before the task begins."


def test_go_mod_exists():
    go_mod_path = os.path.join(PROJECT_DIR, "go.mod")
    assert os.path.isfile(go_mod_path), f"Expected {go_mod_path} to exist before the task begins."


def test_go_mod_pins_pocketbase():
    go_mod_path = os.path.join(PROJECT_DIR, "go.mod")
    with open(go_mod_path) as f:
        content = f.read()
    assert "github.com/pocketbase/pocketbase" in content, \
        "Expected go.mod to declare the github.com/pocketbase/pocketbase dependency."


def test_migrations_package_exists():
    migrations_dir = os.path.join(PROJECT_DIR, "migrations")
    assert os.path.isdir(migrations_dir), f"Expected migrations package directory {migrations_dir} to exist."
    files = [f for f in os.listdir(migrations_dir) if f.endswith(".go")]
    assert len(files) > 0, "Expected at least one .go file inside the migrations package."
