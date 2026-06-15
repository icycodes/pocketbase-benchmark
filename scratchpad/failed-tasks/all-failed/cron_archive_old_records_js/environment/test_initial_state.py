import os
import sqlite3

WORKSPACE = "/workspace"

def test_workspace_exists():
    assert os.path.isdir(WORKSPACE), f"Workspace directory {WORKSPACE} does not exist."

def test_pocketbase_binary_available():
    pb_path = os.path.join(WORKSPACE, "pocketbase")
    assert os.path.isfile(pb_path), "pocketbase binary not found in /workspace."
    assert os.access(pb_path, os.X_OK), "pocketbase binary is not executable."

def test_pb_hooks_dir_exists():
    hooks_dir = os.path.join(WORKSPACE, "pb_hooks")
    assert os.path.isdir(hooks_dir), f"pb_hooks directory {hooks_dir} does not exist."

def test_messages_collection_exists():
    db_path = os.path.join(WORKSPACE, "pb_data", "data.db")
    assert os.path.isfile(db_path), f"Database file {db_path} does not exist."
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM _collections WHERE name='messages'")
    result = cursor.fetchone()
    conn.close()
    assert result is not None, "Collection 'messages' does not exist in the database."
