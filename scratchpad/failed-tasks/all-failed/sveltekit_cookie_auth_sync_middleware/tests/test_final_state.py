import base64
import json
import os
import socket
import time
from http.cookies import SimpleCookie
from urllib.parse import quote, unquote

import pytest
import requests
from xprocess import ProcessStarter

PROJECT_DIR = "/home/user/myproject"
POCKETBASE_URL = "http://127.0.0.1:8090"
SVELTEKIT_URL = "http://127.0.0.1:4173"
SEED_EMAIL = "harbor-user@example.com"
SEED_PASSWORD = "harbor-pass-1234"


def _wait_for_port(host: str, port: int, timeout: float = 60.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except OSError:
            time.sleep(0.5)
    return False


def _b64url_decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def _decode_jwt_payload(token: str) -> dict:
    """Decode the payload of a JWT without verifying the signature."""
    parts = token.split(".")
    assert len(parts) >= 2, f"Token does not look like a JWT: {token!r}"
    payload_bytes = _b64url_decode(parts[1])
    return json.loads(payload_bytes.decode("utf-8"))


def _build_pb_auth_cookie_value(token: str, record: dict) -> str:
    raw = json.dumps({"token": token, "record": record}, separators=(",", ":"))
    return quote(raw, safe="")


def _build_fake_jwt(payload: dict) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    h = base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b"=").decode()
    p = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    s = base64.urlsafe_b64encode(b"fake-signature").rstrip(b"=").decode()
    return f"{h}.{p}.{s}"


def _extract_pb_auth_set_cookie(resp: requests.Response):
    """Return (raw_set_cookie_string, parsed_morsel_dict) for the pb_auth cookie."""
    raw_headers = resp.raw.headers.get_all("Set-Cookie") if hasattr(resp.raw, "headers") else None
    if not raw_headers:
        # Fall back to flattened header (may concatenate multiple set-cookies).
        flat = resp.headers.get("Set-Cookie")
        raw_headers = [flat] if flat else []
    for raw in raw_headers:
        if not raw:
            continue
        # Split potentially-merged cookies (rare, but be defensive).
        # SimpleCookie can parse a single cookie at a time reliably.
        if raw.lstrip().lower().startswith("pb_auth="):
            jar = SimpleCookie()
            jar.load(raw)
            if "pb_auth" in jar:
                return raw, jar["pb_auth"]
    return None, None


def _parse_pb_auth_token(cookie_value: str):
    """Decode the URL-encoded JSON value of a pb_auth cookie and return its token (or '')."""
    if not cookie_value:
        return ""
    try:
        decoded = unquote(cookie_value)
        data = json.loads(decoded)
    except (ValueError, json.JSONDecodeError):
        return ""
    return data.get("token", "") or ""


@pytest.fixture(scope="session")
def authed_session():
    """Authenticate against PocketBase once and return (token, record)."""
    resp = requests.post(
        f"{POCKETBASE_URL}/api/collections/users/auth-with-password",
        json={"identity": SEED_EMAIL, "password": SEED_PASSWORD},
        timeout=15,
    )
    assert resp.status_code == 200, (
        f"Could not authenticate seeded user: status={resp.status_code} "
        f"body={resp.text!r}"
    )
    payload = resp.json()
    token = payload.get("token")
    record = payload.get("record") or {}
    assert token, "PocketBase auth response missing 'token'."
    assert record.get("id"), "PocketBase auth response missing 'record.id'."
    return token, record


@pytest.fixture(scope="session", autouse=True)
def sveltekit_preview(xprocess):
    """Build and start the SvelteKit preview server."""
    # Best-effort clean build before starting the preview server.
    import subprocess

    build = subprocess.run(
        ["npm", "run", "build"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert build.returncode == 0, (
        f"SvelteKit build failed.\nstdout:\n{build.stdout}\nstderr:\n{build.stderr}"
    )

    class Starter(ProcessStarter):
        name = "sveltekit_preview"
        args = ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "4173"]
        env = os.environ.copy()
        popen_kwargs = {
            "cwd": PROJECT_DIR,
            "text": True,
        }
        timeout = 180
        terminate_on_interrupt = True

        def startup_check(self):
            try:
                with socket.create_connection(("127.0.0.1", 4173), timeout=1.0):
                    return True
            except OSError:
                return False

    xprocess.ensure(Starter.name, Starter)
    assert _wait_for_port("127.0.0.1", 4173, timeout=60.0), (
        "SvelteKit preview server did not start on port 4173."
    )

    yield

    info = xprocess.getinfo(Starter.name)
    info.terminate()


def test_whoami_without_cookie_returns_null_user():
    resp = requests.get(f"{SVELTEKIT_URL}/api/whoami", timeout=15)
    assert resp.status_code == 200, (
        f"GET /api/whoami without cookie returned {resp.status_code}: {resp.text!r}"
    )
    body = resp.json()
    assert body == {"user": None}, (
        f"Expected anonymous /api/whoami body to be {{'user': None}}, got {body!r}"
    )


def test_whoami_with_valid_cookie_returns_user_and_refreshes_token(authed_session):
    token, record = authed_session
    cookie_value = _build_pb_auth_cookie_value(token, record)
    exp_before = _decode_jwt_payload(token).get("exp")
    assert isinstance(exp_before, int), (
        f"Expected JWT 'exp' to be an int, got {exp_before!r}"
    )

    # Sleep briefly so the refreshed token's `iat` (and thus `exp`) is strictly larger.
    time.sleep(1.5)

    resp = requests.get(
        f"{SVELTEKIT_URL}/api/whoami",
        headers={"Cookie": f"pb_auth={cookie_value}"},
        timeout=15,
    )
    assert resp.status_code == 200, (
        f"GET /api/whoami with valid cookie returned {resp.status_code}: {resp.text!r}"
    )
    body = resp.json()
    assert isinstance(body, dict) and "user" in body, (
        f"Expected JSON body with 'user' key, got {body!r}"
    )
    user = body["user"]
    assert isinstance(user, dict), (
        f"Expected body['user'] to be an object for an authed request, got {user!r}"
    )
    assert user.get("email") == SEED_EMAIL, (
        f"Expected user.email == {SEED_EMAIL!r}, got {user.get('email')!r}"
    )
    assert user.get("id") == record["id"], (
        f"Expected user.id == {record['id']!r}, got {user.get('id')!r}"
    )

    raw, morsel = _extract_pb_auth_set_cookie(resp)
    assert morsel is not None, (
        f"Response did not include a pb_auth Set-Cookie header. "
        f"Set-Cookie headers were: {resp.headers.get('Set-Cookie')!r}"
    )
    new_token = _parse_pb_auth_token(morsel.value)
    assert new_token, (
        f"pb_auth Set-Cookie did not contain a non-empty token. Raw cookie: {raw!r}"
    )
    exp_after = _decode_jwt_payload(new_token).get("exp")
    assert isinstance(exp_after, int), (
        f"Refreshed JWT 'exp' missing or non-integer: {exp_after!r}"
    )
    assert exp_after > exp_before, (
        f"Expected refreshed JWT exp ({exp_after}) > request JWT exp ({exp_before})."
    )


def test_whoami_with_expired_cookie_returns_null_and_clears_cookie(authed_session):
    _, record = authed_session
    expired_payload = {
        "id": record["id"],
        "type": "auth",
        "collectionId": record.get("collectionId", "_pb_users_auth_"),
        "exp": 1,
    }
    expired_token = _build_fake_jwt(expired_payload)
    cookie_value = _build_pb_auth_cookie_value(expired_token, record)

    resp = requests.get(
        f"{SVELTEKIT_URL}/api/whoami",
        headers={"Cookie": f"pb_auth={cookie_value}"},
        timeout=15,
    )
    assert resp.status_code == 200, (
        f"GET /api/whoami with expired cookie returned {resp.status_code}: {resp.text!r}"
    )
    body = resp.json()
    assert body == {"user": None}, (
        f"Expected body {{'user': None}} for expired cookie, got {body!r}"
    )

    raw, morsel = _extract_pb_auth_set_cookie(resp)
    assert morsel is not None, (
        f"Response did not include a pb_auth Set-Cookie header. "
        f"Set-Cookie headers were: {resp.headers.get('Set-Cookie')!r}"
    )

    cleared_token = _parse_pb_auth_token(morsel.value)
    expires_attr = (morsel["expires"] or "").strip().lower()
    max_age_attr = (morsel["max-age"] or "").strip()

    cleared_by_token = cleared_token == ""
    cleared_by_max_age = max_age_attr in {"0", "-1"}
    cleared_by_expires = expires_attr.startswith("thu, 01 jan 1970") or "1970" in expires_attr

    assert cleared_by_token or cleared_by_max_age or cleared_by_expires, (
        "Expected the pb_auth Set-Cookie response to clear the cookie "
        "(empty token payload, Max-Age=0, or Expires in the past). "
        f"Got raw cookie: {raw!r}"
    )
