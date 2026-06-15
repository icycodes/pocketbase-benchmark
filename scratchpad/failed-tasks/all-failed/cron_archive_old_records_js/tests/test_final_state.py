import os
import sqlite3
import subprocess
import socket
import pytest
import requests
from datetime import datetime, timedelta, timezone
from xprocess import ProcessStarter

WORKSPACE = "/workspace"
DB_PATH = os.path.join(WORKSPACE, "pb_data", "data.db")

@pytest.fixture(scope="session")
def start_app(xprocess):
    class Starter(ProcessStarter):
        name = "pocketbase"
        args = ["./pocketbase", "serve", "--http", "0.0.0.0:8090"]
        env = os.environ.copy()
        popen_kwargs = {
            "cwd": WORKSPACE,
            "text": True,
        }
        timeout = 180
        terminate_on_interrupt = True

        def startup_check(self):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(("localhost", 8090)) == 0

    xprocess.ensure(Starter.name, Starter)
    yield
    info = xprocess.getinfo(Starter.name)
    info.terminate()

def setup_test_data():
    now = datetime.now(timezone.utc)
    old_date = now - timedelta(days=40)
    new_date = now - timedelta(days=10)
    
    old_date_str = old_date.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + "Z"
    new_date_str = new_date.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + "Z"
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Clear existing data
    cursor.execute("DELETE FROM messages")
    
    # Insert old record
    cursor.execute("""
        INSERT INTO messages (id, created, updated, archived)
        VALUES ('oldmessage12345', ?, ?, 0)
    """, (old_date_str, old_date_str))
    
    # Insert new record
    cursor.execute("""
        INSERT INTO messages (id, created, updated, archived)
        VALUES ('newmessage12345', ?, ?, 0)
    """, (new_date_str, new_date_str))
    
    conn.commit()
    conn.close()

def create_superuser():
    subprocess.run(
        ["./pocketbase", "superuser", "upsert", "admin@example.com", "password123456"],
        cwd=WORKSPACE,
        check=True
    )

def get_admin_token():
    resp = requests.post(
        "http://localhost:8090/api/superusers/auth-with-password",
        json={"identity": "admin@example.com", "password": "password123456"}
    )
    resp.raise_for_status()
    return resp.json()["token"]

def test_cron_archives_old_records(start_app):
    # Setup data and superuser
    setup_test_data()
    create_superuser()
    token = get_admin_token()
    
    # Trigger cron job
    resp = requests.post(
        "http://localhost:8090/api/crons/archive_old_messages",
        headers={"Authorization": token}
    )
    assert resp.status_code == 204, f"Failed to trigger cron job: {resp.text}"
    
    # Verify database state
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT archived FROM messages WHERE id='oldmessage12345'")
    old_archived = cursor.fetchone()[0]
    
    cursor.execute("SELECT archived FROM messages WHERE id='newmessage12345'")
    new_archived = cursor.fetchone()[0]
    
    conn.close()
    
    # PocketBase stores boolean as integer (0 or 1) or string depending on schema, but typically 0/1 or "true"/"false".
    # Wait, SQLite boolean is 0 or 1, but PocketBase might store "true" or "false" if it's JSON.
    # Actually, PocketBase maps boolean fields to boolean in SQLite for standard fields, or JSON if dynamic.
    # We can check truthy value.
    assert old_archived in (1, "true", "1", True), "Old record (40 days) was not archived."
    assert new_archived in (0, "false", "0", False), "New record (10 days) was incorrectly archived."
