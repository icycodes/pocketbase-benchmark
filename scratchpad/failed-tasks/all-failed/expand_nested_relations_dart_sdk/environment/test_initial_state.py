import os
import shutil
import subprocess
import time
import urllib.request
import urllib.error
import json
import pytest

PROJECT_DIR = "/home/user/myproject"

def test_dart_binary_available():
    assert shutil.which("dart") is not None, "dart binary not found in PATH."

def test_pocketbase_binary_available():
    assert shutil.which("pocketbase") is not None, "pocketbase binary not found in PATH."

def test_project_dir_exists():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} does not exist."

def test_pocketbase_running_and_seeded():
    # Start PocketBase in the background if it's not running
    try:
        response = urllib.request.urlopen("http://127.0.0.1:8090/api/health")
        if response.getcode() == 200:
            pass # Already running
    except urllib.error.URLError:
        subprocess.Popen(
            ["pocketbase", "serve", "--http", "0.0.0.0:8090", "--dir", "/home/user/pb_data"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        
        # Wait for PocketBase to be ready
        ready = False
        for _ in range(30):
            try:
                if urllib.request.urlopen("http://127.0.0.1:8090/api/health").getcode() == 200:
                    ready = True
                    break
            except Exception:
                pass
            time.sleep(1)
        
        if not ready:
            pytest.fail("PocketBase failed to start on http://127.0.0.1:8090")

    # Seed data
    # Create an admin
    admin_email = "admin@example.com"
    admin_password = "adminpassword123"
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:8090/api/admins",
            data=json.dumps({
                "email": admin_email,
                "password": admin_password,
                "passwordConfirm": admin_password
            }).encode('utf-8'),
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req)
    except urllib.error.HTTPError:
        pass # Admin might already exist
        
    # Authenticate as admin
    req = urllib.request.Request(
        "http://127.0.0.1:8090/api/admins/auth-with-password",
        data=json.dumps({
            "identity": admin_email,
            "password": admin_password
        }).encode('utf-8'),
        headers={"Content-Type": "application/json"}
    )
    response = urllib.request.urlopen(req)
    token = json.loads(response.read().decode('utf-8'))['token']
    headers = {
        "Content-Type": "application/json",
        "Authorization": token
    }
    
    def create_collection(name, schema):
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:8090/api/collections",
                data=json.dumps({
                    "name": name,
                    "type": "base",
                    "schema": schema,
                    "listRule": "",
                    "viewRule": ""
                }).encode('utf-8'),
                headers=headers
            )
            urllib.request.urlopen(req)
        except urllib.error.HTTPError as e:
            pass # Collection might already exist

    # Create collections
    create_collection("level3", [{"name": "name", "type": "text"}])
    create_collection("level2", [{"name": "name", "type": "text"}, {"name": "l3", "type": "relation", "options": {"collectionId": "", "cascadeDelete": False, "minSelect": None, "maxSelect": 1, "displayFields": []}}])
    create_collection("level1", [{"name": "name", "type": "text"}, {"name": "l2", "type": "relation", "options": {"collectionId": "", "cascadeDelete": False, "minSelect": None, "maxSelect": 1, "displayFields": []}}])
    create_collection("root", [{"name": "name", "type": "text"}, {"name": "l1", "type": "relation", "options": {"collectionId": "", "cascadeDelete": False, "minSelect": None, "maxSelect": 1, "displayFields": []}}])
    
    # We need to get collection IDs to update relation options, but PocketBase v0.31.0 allows relation by collection name.
    # We will just use the name for simplicity if possible, but actually let's just create records directly.
    # Wait, in v0.31.0, relations require collectionId.
    def get_collection_id(name):
        req = urllib.request.Request(f"http://127.0.0.1:8090/api/collections/{name}", headers=headers)
        res = urllib.request.urlopen(req)
        return json.loads(res.read().decode('utf-8'))['id']
        
    try:
        l3_col_id = get_collection_id("level3")
        l2_col_id = get_collection_id("level2")
        l1_col_id = get_collection_id("level1")
        
        # Update collections with proper relation options
        def update_relation(col_name, field_name, rel_col_id):
            col_id = get_collection_id(col_name)
            req = urllib.request.Request(
                f"http://127.0.0.1:8090/api/collections/{col_id}",
                data=json.dumps({
                    "schema": [
                        {"name": "name", "type": "text"},
                        {"name": field_name, "type": "relation", "options": {"collectionId": rel_col_id, "maxSelect": 1}}
                    ]
                }).encode('utf-8'),
                headers=headers,
                method="PATCH"
            )
            urllib.request.urlopen(req)
            
        update_relation("level2", "l3", l3_col_id)
        update_relation("level1", "l2", l2_col_id)
        update_relation("root", "l1", l1_col_id)
        
        # Create records
        def create_record(col_name, record_id, data):
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:8090/api/collections/{col_name}/records",
                    data=json.dumps(data | {"id": record_id}).encode('utf-8'),
                    headers=headers
                )
                urllib.request.urlopen(req)
            except urllib.error.HTTPError:
                pass
                
        create_record("level3", "l3record0000001", {"name": "Level 3 Item"})
        create_record("level2", "l2record0000001", {"name": "Level 2 Item", "l3": "l3record0000001"})
        create_record("level1", "l1record0000001", {"name": "Level 1 Item", "l2": "l2record0000001"})
        create_record("root", "rootrecord00001", {"name": "Root Item", "l1": "l1record0000001"})
        
    except Exception as e:
        pytest.fail(f"Failed to seed data: {e}")

    # Verify the root record exists
    try:
        response = urllib.request.urlopen("http://127.0.0.1:8090/api/collections/root/records/rootrecord00001")
        assert response.getcode() == 200, "Root record not found."
    except urllib.error.URLError as e:
        pytest.fail(f"Failed to fetch root record: {e}")
