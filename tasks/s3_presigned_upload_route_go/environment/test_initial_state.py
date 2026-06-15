import os
import shutil
import socket
import subprocess
import time

import pytest

PROJECT_DIR = "/home/user/myapp"
MINIO_ENDPOINT = "http://127.0.0.1:9000"
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "minioadmin"
MINIO_REGION = "us-east-1"
MINIO_BUCKET = "uploads"
POCKETBASE_HTTP_PORT = 8090
MINIO_HTTP_PORT = 9000


def _port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _start_minio_if_needed() -> None:
    """Best-effort ensure that MinIO is reachable on port 9000.

    The Dockerfile is expected to have started MinIO as part of the container
    entrypoint, but the initial-state test is sometimes invoked in
    environments where the entrypoint did not run (e.g. ad-hoc rebuilds), so
    we attempt a fallback boot here. This is idempotent.
    """
    if _port_open("127.0.0.1", MINIO_HTTP_PORT):
        return

    minio_bin = shutil.which("minio")
    if minio_bin is None:
        return

    data_dir = "/var/lib/minio/data"
    os.makedirs(data_dir, exist_ok=True)
    log_path = "/var/log/minio.log"
    env = os.environ.copy()
    env["MINIO_ROOT_USER"] = MINIO_ACCESS_KEY
    env["MINIO_ROOT_PASSWORD"] = MINIO_SECRET_KEY
    with open(log_path, "ab") as log_fp:
        subprocess.Popen(
            [
                minio_bin,
                "server",
                data_dir,
                "--address",
                f":{MINIO_HTTP_PORT}",
                "--console-address",
                ":9001",
            ],
            stdout=log_fp,
            stderr=log_fp,
            env=env,
        )

    deadline = time.time() + 30
    while time.time() < deadline:
        if _port_open("127.0.0.1", MINIO_HTTP_PORT):
            return
        time.sleep(0.5)


def _ensure_bucket() -> None:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError

    s3 = boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        region_name=MINIO_REGION,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )
    try:
        s3.head_bucket(Bucket=MINIO_BUCKET)
    except ClientError:
        s3.create_bucket(Bucket=MINIO_BUCKET)


@pytest.fixture(scope="session", autouse=True)
def _initial_state_setup():
    _start_minio_if_needed()
    _ensure_bucket()
    yield


def test_go_toolchain_available():
    assert shutil.which("go") is not None, (
        "Go toolchain (`go`) not found in PATH; required to build the PocketBase app."
    )


def test_minio_binary_available():
    assert shutil.which("minio") is not None, (
        "MinIO server binary (`minio`) not found in PATH."
    )


def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR), (
        f"Expected project directory {PROJECT_DIR} to exist for the agent to work in."
    )


def test_minio_server_reachable():
    assert _port_open("127.0.0.1", MINIO_HTTP_PORT, timeout=2.0), (
        f"MinIO server is not reachable on 127.0.0.1:{MINIO_HTTP_PORT}."
    )


def test_minio_bucket_exists():
    import boto3
    from botocore.config import Config

    s3 = boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        region_name=MINIO_REGION,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )
    response = s3.head_bucket(Bucket=MINIO_BUCKET)
    status = response["ResponseMetadata"]["HTTPStatusCode"]
    assert status == 200, (
        f"Expected MinIO bucket '{MINIO_BUCKET}' to exist; head_bucket returned {status}."
    )


def test_pocketbase_module_cache_warm():
    """The Dockerfile is expected to pre-warm the Go module cache for
    PocketBase v0.31.0 so that the agent does not need network access to
    fetch the module. The cache lives under $GOPATH/pkg/mod or $GOMODCACHE.
    """
    gomodcache = os.environ.get("GOMODCACHE") or os.path.join(
        os.environ.get("GOPATH", "/root/go"), "pkg", "mod"
    )
    pb_dir = os.path.join(gomodcache, "github.com", "pocketbase")
    assert os.path.isdir(pb_dir), (
        f"Expected the Go module cache directory '{pb_dir}' to contain the "
        "github.com/pocketbase package pre-downloaded."
    )


def test_port_8090_is_free():
    """The agent must be able to bind PocketBase to 0.0.0.0:8090."""
    assert not _port_open("127.0.0.1", POCKETBASE_HTTP_PORT, timeout=0.5), (
        f"Port {POCKETBASE_HTTP_PORT} is already in use; the agent needs it free for PocketBase."
    )
