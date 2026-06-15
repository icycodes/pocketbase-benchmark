import os
import subprocess
import urllib.request
import urllib.parse
import json
import socket
import pytest
from xprocess import ProcessStarter

PROJECT_DIR = "/home/user/dart-realtime"

@pytest.fixture(scope="session")
def start_pocketbase(xprocess):
    """
    Starts the pocketbase service using xprocess. Confirms readiness via port check.
    """
    class Starter(ProcessStarter):
        name = "pocketbase"
        args = ["/usr/local/bin/pocketbase", "serve", "--http=0.0.0.0:8090", "--dir=/pb/pb_data"]
        env = os.environ.copy()
        popen_kwargs = {
            "text": True,
        }
        timeout = 10
        terminate_on_interrupt = True

        def startup_check(self):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(("127.0.0.1", 8090)) == 0

    xprocess.ensure(Starter.name, Starter)
    yield
    info = xprocess.getinfo(Starter.name)
    info.terminate()

def test_dart_app_realtime_subscription(start_pocketbase):
    run_id = os.environ.get("ZEALT_RUN_ID", "default-run-id")
    
    assert os.path.exists(PROJECT_DIR), f"Project directory {PROJECT_DIR} does not exist."
    
    # Run the Dart application
    result = subprocess.run(
        ["dart", "run", "bin/main.dart"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        env=os.environ.copy()
    )
    
    assert result.returncode == 0, f"Dart application failed with error: {result.stderr}"
    
    expected_output = f"Realtime event received: create - Realtime Post {run_id}"
    assert expected_output in result.stdout, f"Expected '{expected_output}' in stdout, got: {result.stdout}"

def test_record_created_in_pocketbase(start_pocketbase):
    run_id = os.environ.get("ZEALT_RUN_ID", "default-run-id")
    
    # Query PocketBase API to verify the record was created
    filter_param = urllib.parse.quote(f"title='Realtime Post {run_id}'")
    url = f"http://127.0.0.1:8090/api/collections/posts/records?filter={filter_param}"
    
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req) as response:
            assert response.status == 200, f"Expected status 200, got {response.status}"
            data = json.loads(response.read().decode())
            assert "items" in data, "Response JSON does not contain 'items'"
            assert len(data["items"]) >= 1, f"No record found with title 'Realtime Post {run_id}'"
            item = data["items"][0]
            assert item["title"] == f"Realtime Post {run_id}", f"Expected title 'Realtime Post {run_id}', got {item['title']}"
    except urllib.error.HTTPError as e:
        pytest.fail(f"HTTP request failed with status {e.code}: {e.read().decode()}")
