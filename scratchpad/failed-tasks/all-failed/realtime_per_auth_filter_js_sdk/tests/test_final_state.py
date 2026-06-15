import os
import subprocess
import socket
import sqlite3
import pytest
from xprocess import ProcessStarter

PROJECT_DIR = "/home/user/myproject"

@pytest.fixture(scope="session")
def start_pocketbase(xprocess):
    """
    Starts the PocketBase server using xprocess. Confirms readiness via port check.
    """
    class Starter(ProcessStarter):
        name = "pocketbase"
        args = ["/usr/local/bin/pocketbase", "serve", "--http=0.0.0.0:8090"]
        env = os.environ.copy()
        popen_kwargs = {
            "cwd": PROJECT_DIR,
            "text": True,
        }
        timeout = 30
        terminate_on_interrupt = True

        def startup_check(self):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(("127.0.0.1", 8090)) == 0

    xprocess.ensure(Starter.name, Starter)
    yield
    info = xprocess.getinfo(Starter.name)
    info.terminate()

def test_script_execution(start_pocketbase):
    """Run the test script and verify output and exit code."""
    result = subprocess.run(
        ["node", "test_realtime.js"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"Script failed with exit code {result.returncode}. Stderr: {result.stderr}\nStdout: {result.stdout}"
    assert "Test passed!" in result.stdout, f"Expected 'Test passed!' in stdout, got: {result.stdout}"

def test_collection_configuration(start_pocketbase):
    """Verify the listRule of the messages collection in the SQLite database."""
    db_path = os.path.join(PROJECT_DIR, "pb_data", "data.db")
    assert os.path.exists(db_path), f"Database file not found at {db_path}"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT listRule FROM _collections WHERE name='messages'")
    row = cursor.fetchone()
    
    assert row is not None, "Collection 'messages' not found in the database."
    list_rule = row[0]
    
    assert list_rule == "user = @request.auth.id", f"Expected listRule 'user = @request.auth.id', got: {list_rule}"
    
    conn.close()
