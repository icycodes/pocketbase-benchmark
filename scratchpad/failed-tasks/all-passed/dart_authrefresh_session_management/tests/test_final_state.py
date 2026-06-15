import base64
import json
import os
import subprocess

import pytest

PROJECT_DIR = "/home/user/myproject"
SESSION_FILE = os.path.join(PROJECT_DIR, "session.json")
PB_BASE_URL = "http://127.0.0.1:8090"
SEED_EMAIL = "user@example.com"
SEED_PASSWORD = "password"


def _decode_jwt_exp(token: str) -> int:
    """Decode the `exp` claim (epoch seconds) from a JWT without verifying the signature."""
    parts = token.split(".")
    assert len(parts) == 3, f"Expected JWT with 3 parts, got {len(parts)} in token={token!r}"
    payload_b64 = parts[1]
    padding = "=" * (-len(payload_b64) % 4)
    payload_json = base64.urlsafe_b64decode(payload_b64 + padding).decode("utf-8")
    payload = json.loads(payload_json)
    exp = payload.get("exp")
    assert isinstance(exp, int), f"Expected integer `exp` claim, got {exp!r}"
    return exp


def _remove_session_file() -> None:
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)


def _run_dart(args, timeout=120):
    return subprocess.run(
        ["dart", "run", "bin/app.dart", *args],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


@pytest.fixture(scope="module", autouse=True)
def _ensure_dependencies():
    """Resolve Dart dependencies once before running the verification steps."""
    pub_get = subprocess.run(
        ["dart", "pub", "get"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert pub_get.returncode == 0, (
        f"`dart pub get` failed in {PROJECT_DIR}: "
        f"stdout={pub_get.stdout!r} stderr={pub_get.stderr!r}"
    )
    yield


def test_login_writes_session_with_non_empty_token():
    _remove_session_file()

    result = _run_dart(["login", SEED_EMAIL, SEED_PASSWORD])
    assert result.returncode == 0, (
        f"Expected `login` to exit 0, got {result.returncode}. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert os.path.isfile(SESSION_FILE), (
        f"Expected session file to be created at {SESSION_FILE} after login."
    )

    with open(SESSION_FILE, "r", encoding="utf-8") as f:
        raw = f.read()
    try:
        session = json.loads(raw)
    except json.JSONDecodeError as exc:
        pytest.fail(f"session.json is not valid JSON after login: {exc}; content={raw!r}")

    assert isinstance(session, dict), (
        f"Expected session.json to contain a JSON object, got {type(session).__name__}."
    )
    token = session.get("token")
    assert isinstance(token, str) and token, (
        f"Expected non-empty `token` field in session.json, got {token!r}."
    )
    assert token.count(".") == 2, (
        f"Expected stored token to be a JWT with two dots, got {token!r}."
    )


def test_refresh_prints_user_id_and_expiry_and_keeps_session_valid():
    # Ensure we have a valid session from a fresh login (idempotent precondition).
    if not os.path.isfile(SESSION_FILE):
        login = _run_dart(["login", SEED_EMAIL, SEED_PASSWORD])
        assert login.returncode == 0, (
            f"Preparatory login failed: stdout={login.stdout!r} stderr={login.stderr!r}"
        )

    result = _run_dart(["refresh"])
    assert result.returncode == 0, (
        f"Expected `refresh` to exit 0, got {result.returncode}. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )

    lines = result.stdout.splitlines()
    assert len(lines) == 2, (
        f"Expected stdout to have exactly two lines after refresh, got {len(lines)}. "
        f"stdout={result.stdout!r}"
    )
    user_id_line, exp_line = lines[0].strip(), lines[1].strip()
    assert user_id_line, "First stdout line (user record id) must not be empty."
    assert exp_line.lstrip("-").isdigit(), (
        f"Second stdout line must be an integer epoch, got {exp_line!r}."
    )
    printed_exp = int(exp_line)

    # Verify the persisted session is still a valid JWT and matches stdout.
    with open(SESSION_FILE, "r", encoding="utf-8") as f:
        session = json.loads(f.read())
    token = session.get("token")
    assert isinstance(token, str) and token, (
        f"Expected non-empty `token` in session.json after refresh, got {token!r}."
    )
    assert token.count(".") == 2, (
        f"Expected stored token after refresh to be a JWT, got {token!r}."
    )

    decoded_exp = _decode_jwt_exp(token)
    assert decoded_exp == printed_exp, (
        f"Printed expiry ({printed_exp}) does not match the `exp` claim of the stored token "
        f"({decoded_exp})."
    )

    # Cross-check that the printed user id matches the one PocketBase returns for the seed user.
    import urllib.request

    payload = json.dumps({"identity": SEED_EMAIL, "password": SEED_PASSWORD}).encode("utf-8")
    req = urllib.request.Request(
        f"{PB_BASE_URL}/api/collections/users/auth-with-password",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    expected_user_id = (body.get("record") or {}).get("id")
    assert expected_user_id, (
        f"Could not determine expected user id from PocketBase for {SEED_EMAIL}."
    )
    assert user_id_line == expected_user_id, (
        f"Expected first stdout line to be the user record id {expected_user_id!r}, "
        f"got {user_id_line!r}."
    )


def test_corrupted_session_emits_invalid_session_and_exits_one():
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        f.write("not-json")

    result = _run_dart(["refresh"])
    assert result.returncode == 1, (
        f"Expected `refresh` with corrupted session to exit 1, got {result.returncode}. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert result.stdout.strip() == "", (
        f"Expected stdout to be empty on corrupted-session error, got {result.stdout!r}."
    )
    assert result.stderr.strip().splitlines()[-1] == "INVALID_SESSION", (
        f"Expected stderr to contain exactly `INVALID_SESSION`, got {result.stderr!r}."
    )
