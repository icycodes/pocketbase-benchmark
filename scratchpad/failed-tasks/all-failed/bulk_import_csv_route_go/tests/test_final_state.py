import os
import pytest
import requests
import socket
import subprocess
from xprocess import ProcessStarter

PROJECT_DIR = "/home/user/pb-app"

@pytest.fixture(scope="session")
def start_app(xprocess):
    # Run go mod tidy before starting
    subprocess.run(["go", "mod", "tidy"], cwd=PROJECT_DIR, check=True)

    class Starter(ProcessStarter):
        name = "pb_app"
        args = ["go", "run", "main.go", "serve", "--http", "0.0.0.0:8090"]
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

def test_valid_csv_import(start_app):
    csv_content = "name,price\nApple,1.5\nBanana,2.0\n"
    csv_path = os.path.join(PROJECT_DIR, "test.csv")
    with open(csv_path, "w") as f:
        f.write(csv_content)

    url = "http://localhost:8090/api/import-csv"
    with open(csv_path, "rb") as f:
        files = {"file": ("test.csv", f, "text/csv")}
        data = {"collection": "products"}
        response = requests.post(url, files=files, data=data)
    
    assert response.status_code == 200, f"Expected status 200, got {response.status_code}: {response.text}"
    json_data = response.json()
    assert "imported" in json_data, f"Expected 'imported' in response, got {json_data}"
    assert json_data["imported"] == 2, f"Expected 2 imported records, got {json_data['imported']}"

def test_verify_records_in_database(start_app):
    url = "http://localhost:8090/api/collections/products/records"
    response = requests.get(url)
    assert response.status_code == 200, f"Expected status 200, got {response.status_code}: {response.text}"
    json_data = response.json()
    assert "items" in json_data, f"Expected 'items' in response, got {json_data}"
    items = json_data["items"]
    
    names = [item.get("name") for item in items]
    assert "Apple" in names, f"Expected 'Apple' in database records, got {names}"
    assert "Banana" in names, f"Expected 'Banana' in database records, got {names}"

def test_invalid_request_missing_file(start_app):
    url = "http://localhost:8090/api/import-csv"
    data = {"collection": "products"}
    response = requests.post(url, data=data)
    assert response.status_code == 400, f"Expected status 400 for missing file, got {response.status_code}: {response.text}"
