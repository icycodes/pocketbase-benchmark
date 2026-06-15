import os
import json
import socket
import pytest
import requests
import boto3
from xprocess import ProcessStarter

PROJECT_DIR = "/home/user/app"

@pytest.fixture(scope="session")
def start_app(xprocess):
    class Starter(ProcessStarter):
        name = "pocketbase_app"
        args = ["go", "run", "main.go", "serve", "--http=0.0.0.0:8090"]
        env = os.environ.copy()
        # Ensure S3 environment variables are set for the app
        env["S3_ENDPOINT"] = "http://127.0.0.1:9000"
        env["S3_REGION"] = "us-east-1"
        env["S3_BUCKET"] = "test-bucket"
        env["S3_ACCESS_KEY"] = "minioadmin"
        env["S3_SECRET_KEY"] = "minioadmin"
        
        popen_kwargs = {
            "cwd": PROJECT_DIR,
            "text": True,
        }
        timeout = 180
        terminate_on_interrupt = True

        def startup_check(self):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(("127.0.0.1", 8090)) == 0

    # Ensure MinIO has the test bucket created before starting the app
    s3_client = boto3.client(
        "s3",
        endpoint_url="http://127.0.0.1:9000",
        aws_access_key_id="minioadmin",
        aws_secret_access_key="minioadmin",
        region_name="us-east-1",
    )
    try:
        s3_client.head_bucket(Bucket="test-bucket")
    except Exception:
        s3_client.create_bucket(Bucket="test-bucket")

    xprocess.ensure(Starter.name, Starter)
    yield
    info = xprocess.getinfo(Starter.name)
    info.terminate()

def test_presigned_upload_flow(start_app):
    # Step 1: Generate Presigned URL
    req_body = {
        "filename": "test_upload.txt",
        "contentType": "text/plain"
    }
    resp = requests.post("http://127.0.0.1:8090/api/presign-upload", json=req_body)
    assert resp.status_code == 200, f"Expected status 200, got {resp.status_code}: {resp.text}"
    
    data = resp.json()
    assert "url" in data, "Response JSON missing 'url' field"
    assert "key" in data, "Response JSON missing 'key' field"
    
    presigned_url = data["url"]
    object_key = data["key"]
    
    # Step 2: Upload File via Presigned URL
    upload_content = "Hello from presigned upload"
    upload_resp = requests.put(
        presigned_url, 
        data=upload_content, 
        headers={"Content-Type": "text/plain"}
    )
    assert upload_resp.status_code == 200, f"Upload to presigned URL failed with status {upload_resp.status_code}: {upload_resp.text}"
    
    # Step 3: Verify File Exists in S3
    s3_client = boto3.client(
        "s3",
        endpoint_url="http://127.0.0.1:9000",
        aws_access_key_id="minioadmin",
        aws_secret_access_key="minioadmin",
        region_name="us-east-1",
    )
    
    try:
        obj = s3_client.get_object(Bucket="test-bucket", Key=object_key)
        content = obj["Body"].read().decode("utf-8")
        assert content == upload_content, f"Expected object content '{upload_content}', got '{content}'"
    except Exception as e:
        pytest.fail(f"Failed to retrieve object from S3: {e}")
