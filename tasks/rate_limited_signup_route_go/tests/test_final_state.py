import os
import socket
import time
import uuid

import pytest
import requests
from xprocess import ProcessStarter

PROJECT_DIR = "/home/user/myproject"
START_SCRIPT = "/home/user/myproject/start.sh"
BASE_URL = "http://127.0.0.1:8090"
HEALTH_URL = f"{BASE_URL}/api/health"
SIGNUP_URL = f"{BASE_URL}/api/collections/users/records"


def _run_id() -> str:
    rid = os.environ.get("ZEALT_RUN_ID", "").strip()
    if rid:
        return rid
    return "zr" + uuid.uuid4().hex[:10]


def _port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        return s.connect_ex(("127.0.0.1", port)) == 0


def _wait_health(timeout: float = 60.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(HEALTH_URL, timeout=2)
            if r.status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(0.5)
    return False


def _wait_bucket_reset(seconds: float = 65.0) -> None:
    # Let any prior 60s-rate-limit window fully expire.
    time.sleep(seconds)


def _signup_payload(prefix: str, idx: int) -> dict:
    rid = _run_id()
    return {
        "email": f"u_{rid}_{prefix}_{idx}_{int(time.time()*1000)%100000}@example.com",
        "password": "Password!123",
        "passwordConfirm": "Password!123",
    }


@pytest.fixture(scope="session")
def start_pocketbase(xprocess):
    assert os.path.isfile(START_SCRIPT) and os.access(START_SCRIPT, os.X_OK), (
        f"Expected an executable start script at {START_SCRIPT}."
    )

    class Starter(ProcessStarter):
        name = "pocketbase_app"
        args = ["bash", START_SCRIPT]
        env = os.environ.copy()
        popen_kwargs = {"cwd": PROJECT_DIR, "text": True}
        timeout = 180
        terminate_on_interrupt = True

        def startup_check(self):
            return _port_open(8090)

    xprocess.ensure(Starter.name, Starter)

    assert _wait_health(timeout=60.0), (
        f"PocketBase did not become healthy at {HEALTH_URL} within 60s."
    )

    yield

    info = xprocess.getinfo(Starter.name)
    info.terminate()


def test_health_endpoint(start_pocketbase):
    r = requests.get(HEALTH_URL, timeout=5)
    assert r.status_code == 200, (
        f"Expected 200 from {HEALTH_URL}, got {r.status_code}: {r.text!r}"
    )


def test_get_users_records_not_rate_limited(start_pocketbase):
    _wait_bucket_reset(65.0)
    statuses = []
    for _ in range(10):
        r = requests.get(SIGNUP_URL, timeout=5)
        statuses.append(r.status_code)
    assert all(s != 429 for s in statuses), (
        f"GET /api/collections/users/records should not be rate-limited, "
        f"but got statuses: {statuses}"
    )


def test_signup_rate_limit_behavior(start_pocketbase):
    _wait_bucket_reset(65.0)

    # 1) Requests 1-3 must NOT be 429.
    first_three_statuses = []
    first_three_bodies = []
    for i in range(1, 4):
        payload = _signup_payload("ok", i)
        r = requests.post(
            SIGNUP_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        first_three_statuses.append(r.status_code)
        first_three_bodies.append(r.text)

    assert all(s != 429 for s in first_three_statuses), (
        f"None of the first 3 signups should be rate-limited (429). "
        f"Got statuses: {first_three_statuses}, bodies: {first_three_bodies}"
    )
    for s in first_three_statuses:
        assert s in (200, 201, 400), (
            f"First 3 signup statuses must be one of 200/201/400, got: "
            f"{first_three_statuses}; bodies: {first_three_bodies}"
        )
    assert any(s in (200, 201) for s in first_three_statuses), (
        f"At least one of the first 3 signups must succeed (200/201), "
        f"but got {first_three_statuses}; bodies: {first_three_bodies}. "
        f"The 'users' collection create rule must allow open signup."
    )

    # 2) Fourth request must be 429 with Retry-After header and JSON retryAfter.
    payload4 = _signup_payload("blocked", 4)
    r4 = requests.post(
        SIGNUP_URL,
        json=payload4,
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    assert r4.status_code == 429, (
        f"Expected the 4th signup within the 60s window to return 429, "
        f"got {r4.status_code}: {r4.text!r}"
    )

    retry_after_header = r4.headers.get("Retry-After")
    assert retry_after_header is not None, (
        f"429 response must include a 'Retry-After' header. Headers: {dict(r4.headers)}"
    )
    try:
        retry_after_seconds = int(retry_after_header.strip())
    except ValueError:
        pytest.fail(
            f"'Retry-After' header must be an integer number of seconds, "
            f"got: {retry_after_header!r}"
        )
    assert 1 <= retry_after_seconds <= 60, (
        f"'Retry-After' header must be between 1 and 60 seconds (inclusive), "
        f"got: {retry_after_seconds}"
    )

    content_type = r4.headers.get("Content-Type", "")
    assert "application/json" in content_type.lower(), (
        f"429 response must be JSON. Content-Type: {content_type!r}, body: {r4.text!r}"
    )
    try:
        body = r4.json()
    except ValueError:
        pytest.fail(f"429 response body must be valid JSON, got: {r4.text!r}")
    assert isinstance(body, dict), (
        f"429 JSON body must be a JSON object, got: {body!r}"
    )
    assert "retryAfter" in body, (
        f"429 JSON body must contain a top-level 'retryAfter' field. Body: {body!r}"
    )
    json_retry_after = body["retryAfter"]
    assert isinstance(json_retry_after, (int, float)), (
        f"'retryAfter' JSON field must be numeric, got: {json_retry_after!r} ({type(json_retry_after).__name__})"
    )
    assert abs(float(json_retry_after) - float(retry_after_seconds)) <= 2.0, (
        f"JSON 'retryAfter' ({json_retry_after}) must equal the 'Retry-After' header "
        f"({retry_after_seconds}) within ±2 seconds."
    )

    # 3) Wait Retry-After + small buffer, then a 5th signup must NOT be 429.
    time.sleep(retry_after_seconds + 1)
    payload5 = _signup_payload("recover", 5)
    r5 = requests.post(
        SIGNUP_URL,
        json=payload5,
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    assert r5.status_code != 429, (
        f"After waiting Retry-After ({retry_after_seconds}s), the 5th signup must not "
        f"be rate-limited. Got {r5.status_code}: {r5.text!r}"
    )
    assert r5.status_code in (200, 201, 400), (
        f"After waiting Retry-After, the 5th signup must return one of 200/201/400. "
        f"Got {r5.status_code}: {r5.text!r}"
    )
