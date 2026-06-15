import os
import re
import urllib.request
import urllib.error
import json
import pytest

PROJECT_DIR = "/home/user/pb-task"
OUTPUT_LOG = os.path.join(PROJECT_DIR, "output.log")
THUMBNAIL_FILE = os.path.join(PROJECT_DIR, "thumbnail.jpg")
INPUT_FILE = os.path.join(PROJECT_DIR, "input.jpg")

def get_record_id():
    if not os.path.isfile(OUTPUT_LOG):
        pytest.fail(f"Log file not found at {OUTPUT_LOG}")
    with open(OUTPUT_LOG, "r") as f:
        content = f.read()
    match = re.search(r"Record ID:\s*([A-Za-z0-9_-]+)", content)
    if not match:
        pytest.fail("Could not find 'Record ID: <id>' in output.log")
    return match.group(1)

def test_output_log_exists_and_contains_record_id():
    get_record_id()

def test_record_exists_in_pocketbase():
    record_id = get_record_id()
    
    # Authenticate to get token
    req = urllib.request.Request("http://127.0.0.1:8090/api/collections/_superusers/auth-with-password", data=json.dumps({
        "identity": "admin@example.com",
        "password": "adminpassword"
    }).encode("utf-8"), headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req)
        auth_data = json.loads(resp.read().decode("utf-8"))
        token = auth_data["token"]
    except Exception as e:
        pytest.fail(f"Failed to authenticate admin to check record: {e}")

    # Fetch record
    req = urllib.request.Request(f"http://127.0.0.1:8090/api/collections/gallery/records/{record_id}", headers={"Authorization": f"Bearer {token}"})
    try:
        resp = urllib.request.urlopen(req)
        record_data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        pytest.fail(f"Failed to fetch record {record_id} from PocketBase: HTTP {e.code}")
    except Exception as e:
        pytest.fail(f"Failed to fetch record {record_id} from PocketBase: {e}")
        
    assert "image" in record_data, "Record does not contain an 'image' field"
    assert record_data["image"], "The 'image' field is empty"

def test_thumbnail_file_exists_and_valid():
    assert os.path.isfile(THUMBNAIL_FILE), f"Thumbnail file not found at {THUMBNAIL_FILE}"
    
    thumb_size = os.path.getsize(THUMBNAIL_FILE)
    assert thumb_size > 0, "Thumbnail file is empty (0 bytes)"
    
    assert os.path.isfile(INPUT_FILE), f"Original input file not found at {INPUT_FILE}"
    input_size = os.path.getsize(INPUT_FILE)
    
    assert thumb_size < input_size, f"Thumbnail size ({thumb_size} bytes) is not smaller than original input size ({input_size} bytes)"
