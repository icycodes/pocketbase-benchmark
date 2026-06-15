import os
import shutil
import stat

PROJECT_DIR = "/home/user/myproject"
POCKETBASE_BIN = os.path.join(PROJECT_DIR, "pocketbase")
HOOKS_DIR = os.path.join(PROJECT_DIR, "pb_hooks")
MIGRATIONS_DIR = os.path.join(PROJECT_DIR, "pb_migrations")
DATA_DIR = os.path.join(PROJECT_DIR, "pb_data")


def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR), (
        f"Project directory {PROJECT_DIR} does not exist."
    )


def test_pocketbase_binary_exists():
    assert os.path.isfile(POCKETBASE_BIN), (
        f"PocketBase binary {POCKETBASE_BIN} does not exist."
    )


def test_pocketbase_binary_is_executable():
    assert os.path.isfile(POCKETBASE_BIN), (
        f"PocketBase binary {POCKETBASE_BIN} does not exist."
    )
    mode = os.stat(POCKETBASE_BIN).st_mode
    assert mode & stat.S_IXUSR, (
        f"PocketBase binary {POCKETBASE_BIN} is not executable by the owner."
    )


def test_pb_hooks_directory_exists():
    assert os.path.isdir(HOOKS_DIR), (
        f"Hooks directory {HOOKS_DIR} does not exist."
    )


def test_pb_migrations_directory_exists():
    assert os.path.isdir(MIGRATIONS_DIR), (
        f"Migrations directory {MIGRATIONS_DIR} does not exist."
    )


def test_pb_data_directory_exists():
    assert os.path.isdir(DATA_DIR), (
        f"Data directory {DATA_DIR} does not exist."
    )


def test_curl_available():
    assert shutil.which("curl") is not None, (
        "curl binary is required for verification but was not found in PATH."
    )
