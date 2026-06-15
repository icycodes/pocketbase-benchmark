import os
import pytest
import requests
import socket
import time
from xprocess import ProcessStarter

PROJECT_DIR = "/home/user/myproject"

@pytest.fixture(scope="session")
def start_pb(xprocess):
    class Starter(ProcessStarter):
        name = "pocketbase"
        args = ["./pocketbase", "serve", "--http=0.0.0.0:8090"]
        env = os.environ.copy()
        popen_kwargs = {
            "cwd": PROJECT_DIR,
            "text": True,
        }
        timeout = 10
        terminate_on_interrupt = True

        def startup_check(self):
            for _ in range(30):
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    if s.connect_ex(("localhost", 8090)) == 0:
                        return True
                time.sleep(0.5)
            return False

    xprocess.ensure(Starter.name, Starter)
    yield
    info = xprocess.getinfo(Starter.name)
    info.terminate()

def test_custom_stats_route(start_pb):
    # 1. Create sample data
    scores = [10, 25, 15]
    for score in scores:
        resp = requests.post(
            "http://localhost:8090/api/collections/game_scores/records",
            json={"score": score}
        )
        assert resp.status_code == 200, f"Failed to create record: {resp.text}"
    
    # 2. Get aggregated stats
    resp = requests.get("http://localhost:8090/api/stats")
    assert resp.status_code == 200, f"Expected status 200 from /api/stats, got {resp.status_code}. Response: {resp.text}"
    
    data = resp.json()
    assert "count" in data, "Response JSON is missing 'count' field."
    assert "sum" in data, "Response JSON is missing 'sum' field."
    
    assert data["count"] == 3, f"Expected count to be 3, got {data['count']}"
    assert data["sum"] == 50, f"Expected sum to be 50, got {data['sum']}"
