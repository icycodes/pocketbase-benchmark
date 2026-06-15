import os
import shutil
import sqlite3

PROJECT_DIR = "/home/user/myproject"
PB_DATA_DB = os.path.join(PROJECT_DIR, "pb_data", "data.db")
GO_MOD = os.path.join(PROJECT_DIR, "go.mod")


def test_go_binary_available():
    assert shutil.which("go") is not None, "Go toolchain ('go') not found in PATH."


def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} does not exist."


def test_go_module_initialized_with_pocketbase_v0_31_0():
    assert os.path.isfile(GO_MOD), f"Go module file {GO_MOD} does not exist."
    with open(GO_MOD, "r", encoding="utf-8") as fh:
        contents = fh.read()
    assert "github.com/pocketbase/pocketbase" in contents, (
        "go.mod does not reference 'github.com/pocketbase/pocketbase'."
    )
    assert "v0.31.0" in contents, "go.mod does not pin PocketBase to v0.31.0."


def test_pb_data_database_exists():
    assert os.path.isfile(PB_DATA_DB), (
        f"PocketBase data file {PB_DATA_DB} does not exist; collections were not seeded."
    )


def test_posts_collection_seeded():
    conn = sqlite3.connect(PB_DATA_DB)
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM _collections WHERE name = ?", ("posts",))
        row = cur.fetchone()
        assert row is not None, "Collection 'posts' was not pre-created in pb_data/data.db."
    finally:
        conn.close()


def test_audit_log_collection_seeded():
    conn = sqlite3.connect(PB_DATA_DB)
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM _collections WHERE name = ?", ("audit_log",))
        row = cur.fetchone()
        assert row is not None, (
            "Collection 'audit_log' was not pre-created in pb_data/data.db."
        )
    finally:
        conn.close()


def test_regular_user_seeded():
    conn = sqlite3.connect(PB_DATA_DB)
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE email = ?", ("user@example.com",))
        row = cur.fetchone()
        assert row is not None, (
            "Regular user 'user@example.com' was not pre-seeded in the users collection."
        )
    finally:
        conn.close()
