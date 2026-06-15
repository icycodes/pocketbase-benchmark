import os
import time
import uuid

import pytest
import requests

PB_URL = os.environ.get("PB_URL", "http://127.0.0.1:8090")
USERS_ENDPOINT = f"{PB_URL}/api/collections/users/records"


def _wait_for_health(timeout_sec: float = 60.0) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            r = requests.get(f"{PB_URL}/api/health", timeout=5)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


@pytest.fixture(scope="session", autouse=True)
def ensure_pb_ready():
    assert _wait_for_health(timeout_sec=90.0), (
        f"PocketBase server at {PB_URL} did not become healthy."
    )
    # Give the JSVM a moment to pick up newly placed hook files.
    time.sleep(2.0)
    yield


def _unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}@example.com"


def _post_user(email: str, password: str) -> requests.Response:
    return requests.post(
        USERS_ENDPOINT,
        json={
            "email": email,
            "password": password,
            "passwordConfirm": password,
        },
        headers={"Content-Type": "application/json"},
        timeout=15,
    )


def _password_code(resp: requests.Response):
    try:
        body = resp.json()
    except Exception as e:
        pytest.fail(f"Response was not valid JSON: {e}; raw={resp.text!r}")
    data = body.get("data")
    assert isinstance(data, dict), (
        f"Expected `data` object in response body, got: {body!r}"
    )
    password_err = data.get("password")
    assert isinstance(password_err, dict), (
        f"Expected `data.password` object in response body, got: {body!r}"
    )
    code = password_err.get("code")
    assert isinstance(code, str), (
        f"Expected `data.password.code` to be a string, got: {body!r}"
    )
    return code


def test_valid_password_creates_user():
    email = _unique_email("alice1")
    password = "GoodPass1!xyzQ"  # 14 chars, upper/lower/digit/symbol, no email local-part
    resp = _post_user(email, password)
    assert resp.status_code == 200, (
        f"Expected 200 for valid password, got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    assert body.get("id"), (
        f"Expected created record to have an `id`, got: {body!r}"
    )
    assert body.get("email", "").lower() == email.lower(), (
        f"Expected response email to match request, got: {body!r}"
    )


def test_too_short_password_returns_pwd_len():
    email = _unique_email("alice2")
    password = "Ab1!xyz"  # 7 chars, fails length check
    resp = _post_user(email, password)
    assert resp.status_code == 400, (
        f"Expected 400 for too-short password, got {resp.status_code}: {resp.text}"
    )
    code = _password_code(resp)
    assert code == "PWD_LEN", (
        f"Expected data.password.code == 'PWD_LEN', got {code!r}; body={resp.text}"
    )


def test_missing_uppercase_returns_pwd_upper():
    email = _unique_email("alice3")
    password = "goodpass1!xyzq"  # no uppercase
    resp = _post_user(email, password)
    assert resp.status_code == 400, (
        f"Expected 400 for missing uppercase, got {resp.status_code}: {resp.text}"
    )
    code = _password_code(resp)
    assert code == "PWD_UPPER", (
        f"Expected data.password.code == 'PWD_UPPER', got {code!r}; body={resp.text}"
    )


def test_missing_digit_returns_pwd_digit():
    email = _unique_email("alice4")
    password = "GoodPassNoDig!xyz"  # no digit
    resp = _post_user(email, password)
    assert resp.status_code == 400, (
        f"Expected 400 for missing digit, got {resp.status_code}: {resp.text}"
    )
    code = _password_code(resp)
    assert code == "PWD_DIGIT", (
        f"Expected data.password.code == 'PWD_DIGIT', got {code!r}; body={resp.text}"
    )


def test_missing_symbol_returns_pwd_symbol():
    email = _unique_email("alice5")
    password = "GoodPass1xyzABCD"  # no symbol from !@#$%^&*
    resp = _post_user(email, password)
    assert resp.status_code == 400, (
        f"Expected 400 for missing symbol, got {resp.status_code}: {resp.text}"
    )
    code = _password_code(resp)
    assert code == "PWD_SYMBOL", (
        f"Expected data.password.code == 'PWD_SYMBOL', got {code!r}; body={resp.text}"
    )


def test_password_contains_email_local_part_returns_pwd_contains_email():
    # local-part is "Charlie<suffix>"; password contains "Charlie" case-insensitively.
    local = f"Charlie{uuid.uuid4().hex[:6]}"
    email = f"{local}@example.com"
    # Choose a password that satisfies all other rules but contains the local-part substring.
    password = f"X{local}1A!bcdef"
    resp = requests.post(
        USERS_ENDPOINT,
        json={
            "email": email,
            "password": password,
            "passwordConfirm": password,
        },
        headers={"Content-Type": "application/json"},
        timeout=15,
    )
    assert resp.status_code == 400, (
        f"Expected 400 for password containing email local-part, got "
        f"{resp.status_code}: {resp.text}"
    )
    code = _password_code(resp)
    assert code == "PWD_CONTAINS_EMAIL", (
        f"Expected data.password.code == 'PWD_CONTAINS_EMAIL', got {code!r}; "
        f"body={resp.text}"
    )
