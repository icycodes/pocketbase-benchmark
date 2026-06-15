import os
import subprocess
import json
import pytest
import time
import urllib.request
import urllib.error

PROJECT_DIR = "/home/user/myproject"
ROOT_RECORD_ID = "rootrecord00001"

def test_pocketbase_running():
    """Ensure PocketBase is still running."""
    max_retries = 30
    for _ in range(max_retries):
        try:
            response = urllib.request.urlopen("http://127.0.0.1:8090/api/health")
            if response.getcode() == 200:
                return
        except urllib.error.URLError:
            pass
        time.sleep(1)
    pytest.fail("PocketBase is not running on http://127.0.0.1:8090")

def test_dart_pub_get():
    """Ensure dependencies are installed."""
    result = subprocess.run(
        ["dart", "pub", "get"],
        capture_output=True,
        text=True,
        cwd=PROJECT_DIR
    )
    assert result.returncode == 0, f"'dart pub get' failed: {result.stderr}"

def test_dart_script_output():
    """Run the Dart script and verify the expanded nested relations in stdout."""
    result = subprocess.run(
        ["dart", "run", "main.dart", ROOT_RECORD_ID],
        capture_output=True,
        text=True,
        cwd=PROJECT_DIR
    )
    
    assert result.returncode == 0, f"'dart run main.dart {ROOT_RECORD_ID}' failed: {result.stderr}"
    
    # Try to parse the stdout as JSON. Sometimes the output contains other logs, 
    # so we might need to extract the JSON part. For simplicity, we assume the last line or the whole output is JSON.
    try:
        # Find the first '{' and last '}' to extract JSON in case there are other logs
        stdout_str = result.stdout.strip()
        start_idx = stdout_str.find('{')
        end_idx = stdout_str.rfind('}')
        if start_idx == -1 or end_idx == -1:
            pytest.fail(f"No JSON object found in stdout: {result.stdout}")
            
        json_str = stdout_str[start_idx:end_idx+1]
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        pytest.fail(f"Failed to parse stdout as JSON: {e}\nStdout: {result.stdout}")

    # Check the nested structure
    try:
        expand_l1 = data.get("expand", {}).get("l1", {})
        assert expand_l1, "Missing 'expand.l1' in JSON output."
        
        expand_l2 = expand_l1.get("expand", {}).get("l2", {})
        assert expand_l2, "Missing 'expand.l1.expand.l2' in JSON output."
        
        expand_l3 = expand_l2.get("expand", {}).get("l3", {})
        assert expand_l3, "Missing 'expand.l1.expand.l2.expand.l3' in JSON output."
        
        l3_name = expand_l3.get("name")
        assert l3_name == "Level 3 Item", f"Expected 'Level 3 Item', got '{l3_name}'"
    except AttributeError:
        pytest.fail(f"JSON structure does not match expected nested objects: {data}")
