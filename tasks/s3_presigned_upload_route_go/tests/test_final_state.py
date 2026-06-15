import io
import os
import re
import socket
import subprocess
import time
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs

import boto3
import pytest
import requests
from botocore.config import Config
from botocore.exceptions import ClientError
from xprocess import ProcessStarter

PROJECT_DIR = "/home/user/myapp"
PB_BIN = os.path.join(PROJECT_DIR, "myapp")
PB_HTTP = "http://127.0.0.1:8090"
PB_PORT = 8090

MINIO_ENDPOINT = "http://127.0.0.1:9000"
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "minioadmin"
MINIO_REGION = "us-east-1"
MINIO_BUCKET = "uploads"

SUPERUSER_EMAIL = "admin@example.com"
SUPERUSER_PASSWORD = "1234567890"
USER_EMAIL = "user@example.com"
USER_PASSWORD = "password1234"
OTHER_EMAIL = "other@example.com"
OTHER_PASSWORD = "password1234"

KEY_RE = re.compile(r"^[a-f0-9-]{16,}$")


def _port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _ensure_built() -> None:
    """If the agent did not build the binary, build it for them so we can run it."""
    if os.path.isfile(PB_BIN) and os.access(PB_BIN, os.X_OK):
        return
    result = subprocess.run(
        ["go", "build", "-o", "myapp", "."],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0 and os.path.isfile(PB_BIN), (
        "The agent did not produce a usable binary and `go build` also failed.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def _kill_port(port: int) -> None:
    try:
        subprocess.run(["fuser", "-k", f"{port}/tcp"], capture_output=True, check=False)
    except FileNotFoundError:
        # try lsof+kill as a fallback
        try:
            out = subprocess.run(
                ["lsof", "-ti", f"tcp:{port}"], capture_output=True, text=True, check=False
            )
            for pid in (out.stdout or "").split():
                subprocess.run(["kill", "-9", pid], capture_output=True, check=False)
        except FileNotFoundError:
            pass


@pytest.fixture(scope="session")
def pb_app(xprocess):
    _kill_port(PB_PORT)
    _ensure_built()

    class Starter(ProcessStarter):
        name = "pb_app"
        args = [PB_BIN, "serve", "--http=0.0.0.0:8090"]
        env = os.environ.copy()
        popen_kwargs = {
            "cwd": PROJECT_DIR,
            "text": True,
        }
        timeout = 60
        terminate_on_interrupt = True

        def startup_check(self):
            try:
                r = requests.get(f"{PB_HTTP}/api/health", timeout=2)
                return r.status_code == 200
            except requests.RequestException:
                return False

    xprocess.ensure(Starter.name, Starter)
    yield
    info = xprocess.getinfo(Starter.name)
    info.terminate()


def _auth(collection: str, identity: str, password: str) -> dict:
    r = requests.post(
        f"{PB_HTTP}/api/collections/{collection}/auth-with-password",
        json={"identity": identity, "password": password},
        timeout=10,
    )
    assert r.status_code == 200, (
        f"Failed to authenticate {identity} against collection '{collection}': "
        f"{r.status_code} {r.text}"
    )
    data = r.json()
    return data


@pytest.fixture(scope="session")
def user_token(pb_app) -> str:
    return _auth("users", USER_EMAIL, USER_PASSWORD)["token"]


@pytest.fixture(scope="session")
def other_token(pb_app) -> str:
    return _auth("users", OTHER_EMAIL, OTHER_PASSWORD)["token"]


@pytest.fixture(scope="session")
def super_token(pb_app) -> str:
    return _auth("_superusers", SUPERUSER_EMAIL, SUPERUSER_PASSWORD)["token"]


@pytest.fixture(scope="session")
def user_id(pb_app) -> str:
    return _auth("users", USER_EMAIL, USER_PASSWORD)["record"]["id"]


@pytest.fixture(scope="session")
def s3_client():
    return boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        region_name=MINIO_REGION,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def _presign(token: str | None) -> requests.Response:
    headers = {}
    if token:
        headers["Authorization"] = token
    return requests.post(f"{PB_HTTP}/api/uploads/presign", headers=headers, timeout=15)


def _finalize(token: str | None, key: str) -> requests.Response:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = token
    return requests.post(
        f"{PB_HTTP}/api/uploads/finalize",
        headers=headers,
        json={"key": key},
        timeout=15,
    )


def _list_records(super_token: str, collection: str, key: str) -> list[dict]:
    r = requests.get(
        f"{PB_HTTP}/api/collections/{collection}/records",
        headers={"Authorization": super_token},
        params={"filter": f'key="{key}"', "perPage": 50},
        timeout=10,
    )
    assert r.status_code == 200, (
        f"Failed to list records from '{collection}' as superuser: {r.status_code} {r.text}"
    )
    return r.json().get("items", [])


def _parse_rfc3339(s: str) -> datetime:
    # accept both `Z` and explicit offset and the PocketBase-style space-separated form
    txt = s.strip().replace(" ", "T")
    if txt.endswith("Z"):
        txt = txt[:-1] + "+00:00"
    return datetime.fromisoformat(txt)


def test_presign_requires_auth(pb_app):
    r = _presign(None)
    assert r.status_code == 401, (
        f"Expected unauthenticated POST /api/uploads/presign to return 401, "
        f"got {r.status_code}: {r.text}"
    )


def test_finalize_requires_auth(pb_app):
    r = requests.post(
        f"{PB_HTTP}/api/uploads/finalize",
        json={"key": "anything"},
        timeout=10,
    )
    assert r.status_code == 401, (
        f"Expected unauthenticated POST /api/uploads/finalize to return 401, "
        f"got {r.status_code}: {r.text}"
    )


def test_presign_success_shape(pb_app, user_token, super_token, user_id):
    sent_at = datetime.now(tz=timezone.utc)
    r = _presign(user_token)
    assert r.status_code == 200, (
        f"Authenticated /presign should return 200, got {r.status_code}: {r.text}"
    )
    body = r.json()
    assert "url" in body and "key" in body and "expiresAt" in body, (
        f"/presign response missing required fields. Got keys: {list(body.keys())}"
    )

    key = body["key"]
    url = body["url"]
    expires_at = body["expiresAt"]

    assert isinstance(key, str) and KEY_RE.match(key), (
        f"Returned `key` does not look like a uuid-like string (regex {KEY_RE.pattern!r}): {key!r}"
    )

    parsed = urlparse(url)
    assert parsed.scheme in {"http", "https"}, (
        f"Presigned `url` must use http(s) scheme; got {parsed.scheme!r}"
    )
    assert parsed.netloc in {"127.0.0.1:9000", "localhost:9000"}, (
        f"Presigned `url` must point at the local MinIO instance (127.0.0.1:9000 / "
        f"localhost:9000); got netloc {parsed.netloc!r}"
    )
    assert parsed.path.endswith(f"/{MINIO_BUCKET}/{key}"), (
        f"Presigned `url` path must end with /{MINIO_BUCKET}/{{key}}, got path {parsed.path!r}"
    )
    qs = parse_qs(parsed.query)
    assert "X-Amz-Signature" in qs, (
        f"Presigned `url` must be AWS SigV4 (contain X-Amz-Signature); got query {parsed.query!r}"
    )
    assert qs.get("X-Amz-Expires") == ["300"], (
        f"Presigned `url` must use X-Amz-Expires=300, got {qs.get('X-Amz-Expires')!r}"
    )

    expires_dt = _parse_rfc3339(expires_at)
    delta = (expires_dt - sent_at).total_seconds()
    assert 299 <= delta <= 360, (
        f"`expiresAt` must be 299..360s in the future relative to the request; "
        f"got delta={delta:.1f}s (expiresAt={expires_at!r})"
    )

    pending = _list_records(super_token, "pending_upload", key)
    assert len(pending) == 1, (
        f"Expected exactly 1 pending_upload record for key {key!r}, got {len(pending)}"
    )
    row = pending[0]
    assert row.get("user") == user_id, (
        f"pending_upload.user must equal the authenticated user's id "
        f"({user_id!r}), got {row.get('user')!r}"
    )


def test_full_upload_and_finalize_flow(pb_app, user_token, super_token, user_id, s3_client):
    r = _presign(user_token)
    assert r.status_code == 200, f"/presign failed: {r.status_code} {r.text}"
    body = r.json()
    key = body["key"]
    url = body["url"]

    payload = os.urandom(32)
    put = requests.put(url, data=payload, timeout=15)
    assert put.status_code in {200, 204}, (
        f"PUT to presigned MinIO URL must return 200/204; got {put.status_code}: {put.text}"
    )

    head = s3_client.head_object(Bucket=MINIO_BUCKET, Key=key)
    assert head["ResponseMetadata"]["HTTPStatusCode"] == 200, (
        f"Object {key!r} should exist in MinIO after PUT; head_object did not return 200"
    )
    assert int(head["ContentLength"]) == 32, (
        f"Uploaded object should be 32 bytes, head_object reported {head['ContentLength']}"
    )

    fin = _finalize(user_token, key)
    assert fin.status_code == 200, (
        f"/finalize for existing object should return 200; got {fin.status_code}: {fin.text}"
    )
    fin_body = fin.json()
    assert fin_body.get("key") == key, (
        f"/finalize response must echo `key`; expected {key!r}, got {fin_body!r}"
    )

    pending_after = _list_records(super_token, "pending_upload", key)
    assert len(pending_after) == 0, (
        f"pending_upload row for key {key!r} should be removed after finalize; "
        f"found {len(pending_after)}"
    )

    uploads_after = _list_records(super_token, "uploads", key)
    assert len(uploads_after) == 1, (
        f"`uploads` collection should contain exactly one row for key {key!r}; "
        f"got {len(uploads_after)}"
    )
    assert uploads_after[0].get("user") == user_id, (
        f"`uploads.user` must equal the authenticated user's id ({user_id!r}); "
        f"got {uploads_after[0].get('user')!r}"
    )


def test_finalize_missing_object_returns_404(pb_app, user_token):
    r = _presign(user_token)
    assert r.status_code == 200, f"/presign failed: {r.status_code} {r.text}"
    key = r.json()["key"]

    # Sanity: ensure the object truly does not exist (presign should not have
    # caused the bytes to materialize in MinIO).
    s3 = boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        region_name=MINIO_REGION,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )
    with pytest.raises(ClientError):
        s3.head_object(Bucket=MINIO_BUCKET, Key=key)

    fin = _finalize(user_token, key)
    assert fin.status_code == 404, (
        f"/finalize for a key whose object does not exist must return 404; "
        f"got {fin.status_code}: {fin.text}"
    )


def test_user_cannot_finalize_other_users_key(pb_app, user_token, other_token, s3_client):
    r = _presign(user_token)
    assert r.status_code == 200, f"/presign failed: {r.status_code} {r.text}"
    key = r.json()["key"]

    # Put bytes for `key` so the object EXISTS — the only reason to reject the
    # other user's finalize is ownership.
    s3_client.put_object(Bucket=MINIO_BUCKET, Key=key, Body=b"abcdefgh")

    cross = _finalize(other_token, key)
    assert cross.status_code == 404, (
        f"User other@example.com must not be able to finalize a key owned by "
        f"user@example.com; expected 404, got {cross.status_code}: {cross.text}"
    )

    # The original owner should still be able to finalize the key.
    owner_fin = _finalize(user_token, key)
    assert owner_fin.status_code == 200, (
        f"Original owner must still be able to finalize their own key after the "
        f"cross-user attempt; got {owner_fin.status_code}: {owner_fin.text}"
    )
