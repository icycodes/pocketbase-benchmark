import os
import requests
import socket
import pytest
import subprocess
from xprocess import ProcessStarter

PROJECT_DIR = "/home/user/myproject"

@pytest.fixture(scope="session", autouse=True)
def build_pb():
    """Build the PocketBase application before starting it."""
    result = subprocess.run(
        ["go", "build", "-o", "pb", "main.go"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"Failed to build PocketBase: {result.stderr}"

@pytest.fixture(scope="session")
def start_app(xprocess):
    """Starts the PocketBase server using xprocess."""
    class Starter(ProcessStarter):
        name = "start_pb"
        args = ["./pb", "serve", "--http=0.0.0.0:8090"]
        env = os.environ.copy()
        popen_kwargs = {
            "cwd": PROJECT_DIR,
            "text": True,
        }
        timeout = 60
        terminate_on_interrupt = True

        def startup_check(self):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(("localhost", 8090)) == 0

    xprocess.ensure(Starter.name, Starter)
    yield
    info = xprocess.getinfo(Starter.name)
    info.terminate()

def test_configs_collection_seeded_records(start_app):
    """Verify that the configs collection exists and contains the seeded records."""
    url = "http://localhost:8090/api/collections/configs/records"
    try:
        response = requests.get(url)
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Failed to connect to the API: {e}")
        
    assert response.status_code == 200, f"Expected status 200, got {response.status_code}. Response: {response.text}"
    
    data = response.json()
    assert "totalItems" in data, "Response JSON missing 'totalItems' field."
    assert data["totalItems"] == 2, f"Expected 2 total items, got {data['totalItems']}."
    
    assert "items" in data, "Response JSON missing 'items' field."
    items = data["items"]
    assert len(items) == 2, f"Expected 2 items in array, got {len(items)}."
    
    # Extract key-value pairs from items
    kv_pairs = {item.get("key"): item.get("value") for item in items}
    
    assert "site_name" in kv_pairs, "Expected 'site_name' key not found in records."
    assert kv_pairs["site_name"] == "My Site", f"Expected value 'My Site' for 'site_name', got {kv_pairs['site_name']}."
    
    assert "maintenance_mode" in kv_pairs, "Expected 'maintenance_mode' key not found in records."
    assert kv_pairs["maintenance_mode"] == "false", f"Expected value 'false' for 'maintenance_mode', got {kv_pairs['maintenance_mode']}."
