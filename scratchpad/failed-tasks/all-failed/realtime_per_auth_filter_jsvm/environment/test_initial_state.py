import os
import shutil
import subprocess

import pytest
import requests
from xprocess import ProcessStarter

PROJECT_DIR = "/home/user/myproject"
PB_BIN = os.path.join(PROJECT_DIR, "pocketbase")
PB_DATA = os.path.join(PROJECT_DIR, "pb_data")
PB_URL = "http://127.0.0.1:8090"


@pytest.fixture(scope="session")
def pb_server(xprocess):
    """Start the PocketBase server for the initial-state checks.

    The server is kept running until the pytest session ends so that it is
    available for the executing agent immediately after this test suite
    finishes.
    """

    class Starter(ProcessStarter):
        name = "pb_server_init"
        args = [PB_BIN, "serve", "--http=0.0.0.0:8090"]
        # MUST be a class attribute (NOT inside popen_kwargs) per xprocess docs.
        env = os.environ.copy()
        popen_kwargs = {
            "cwd": PROJECT_DIR,
            "text": True,
        }
        timeout = 60
        terminate_on_interrupt = True

        def startup_check(self):
            try:
                r = requests.get(f"{PB_URL}/api/health", timeout=2)
                return r.status_code == 200
            except Exception:
                return False

    xprocess.ensure(Starter.name, Starter)
    yield
    info = xprocess.getinfo(Starter.name)
    info.terminate()


def test_pocketbase_binary_present():
    assert os.path.isfile(PB_BIN), (
        f"PocketBase binary not found at {PB_BIN}. The environment is "
        "expected to ship the v0.31.0 binary in the project directory."
    )
    assert os.access(PB_BIN, os.X_OK), (
        f"PocketBase binary at {PB_BIN} is not executable."
    )


def test_pocketbase_version_is_v0_31_0():
    result = subprocess.run(
        [PB_BIN, "--version"],
        capture_output=True,
        text=True,
        cwd=PROJECT_DIR,
    )
    assert result.returncode == 0, (
        f"`pocketbase --version` failed: stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    combined = (result.stdout or "") + (result.stderr or "")
    assert "0.31.0" in combined, (
        f"Expected PocketBase v0.31.0 in the version output, got: {combined!r}"
    )


def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR), (
        f"Expected project directory {PROJECT_DIR} to exist."
    )


def test_pb_data_initialized():
    assert os.path.isdir(PB_DATA), (
        f"Expected pb_data directory at {PB_DATA} (initial seed missing)."
    )
    db_path = os.path.join(PB_DATA, "data.db")
    assert os.path.isfile(db_path), (
        f"Expected SQLite database file at {db_path} (pb_data not seeded)."
    )


def test_requests_module_available():
    # The verifier and the executor rely on the `requests` package being
    # importable for HTTP-based interactions with PocketBase.
    import requests as _r  # noqa: F401


def test_curl_available():
    assert shutil.which("curl") is not None, (
        "Expected `curl` to be available on PATH for ad-hoc API calls."
    )


def test_superuser_auth_works(pb_server):
    r = requests.post(
        f"{PB_URL}/api/collections/_superusers/auth-with-password",
        json={"identity": "admin@example.com", "password": "SuperAdmin1234"},
        timeout=10,
    )
    assert r.status_code == 200, (
        f"Superuser auth failed (expected the environment to seed the "
        f"`admin@example.com` superuser): status={r.status_code} body={r.text!r}"
    )
    assert "token" in r.json(), (
        f"Superuser auth response missing `token`: {r.text!r}"
    )


def test_user_alice_seeded(pb_server):
    r = requests.post(
        f"{PB_URL}/api/collections/users/auth-with-password",
        json={"identity": "alice@example.com", "password": "AlicePass1234"},
        timeout=10,
    )
    assert r.status_code == 200, (
        f"Expected pre-seeded user `alice@example.com` with password "
        f"`AlicePass1234` to authenticate successfully: status={r.status_code} "
        f"body={r.text!r}"
    )
    record = r.json().get("record", {})
    assert record.get("email") == "alice@example.com", (
        f"Auth response for Alice did not return the expected email: {r.text!r}"
    )


def test_user_bob_seeded(pb_server):
    r = requests.post(
        f"{PB_URL}/api/collections/users/auth-with-password",
        json={"identity": "bob@example.com", "password": "BobPass1234"},
        timeout=10,
    )
    assert r.status_code == 200, (
        f"Expected pre-seeded user `bob@example.com` with password "
        f"`BobPass1234` to authenticate successfully: status={r.status_code} "
        f"body={r.text!r}"
    )
    record = r.json().get("record", {})
    assert record.get("email") == "bob@example.com", (
        f"Auth response for Bob did not return the expected email: {r.text!r}"
    )
