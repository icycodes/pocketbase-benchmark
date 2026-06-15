import os
import time
import subprocess
import requests
import pytest

PROJECT_DIR = "/home/user/app"
PB_BINARY = os.path.join(PROJECT_DIR, "pocketbase")

def test_pocketbase_binary_exists():
    assert os.path.isfile(PB_BINARY), f"PocketBase binary not found at {PB_BINARY}"
    assert os.access(PB_BINARY, os.X_OK), f"PocketBase binary at {PB_BINARY} is not executable"

def test_collections_exist():
    # Start PocketBase in the background
    process = subprocess.Popen(
        [PB_BINARY, "serve", "--http=127.0.0.1:8090"],
        cwd=PROJECT_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    try:
        # Wait for server to start
        time.sleep(2)
        
        # Check projects collection
        resp = requests.get("http://127.0.0.1:8090/api/collections/projects")
        assert resp.status_code == 200, "Collection 'projects' does not exist"
        projects_schema = resp.json().get("fields", [])
        members_field = next((f for f in projects_schema if f["name"] == "members"), None)
        assert members_field is not None, "'members' field not found in 'projects' collection"
        assert members_field["type"] == "relation", "'members' field should be a relation"
        
        # Check tasks collection
        resp = requests.get("http://127.0.0.1:8090/api/collections/tasks")
        assert resp.status_code == 200, "Collection 'tasks' does not exist"
        tasks_schema = resp.json().get("fields", [])
        project_field = next((f for f in tasks_schema if f["name"] == "project"), None)
        assert project_field is not None, "'project' field not found in 'tasks' collection"
        assert project_field["type"] == "relation", "'project' field should be a relation"
        
        # Check that API rules are insecure or empty initially
        tasks_data = resp.json()
        assert tasks_data.get("listRule") is None or tasks_data.get("listRule") == "", "tasks listRule should be empty initially"
        assert tasks_data.get("viewRule") is None or tasks_data.get("viewRule") == "", "tasks viewRule should be empty initially"
        
    finally:
        process.terminate()
        process.wait()
