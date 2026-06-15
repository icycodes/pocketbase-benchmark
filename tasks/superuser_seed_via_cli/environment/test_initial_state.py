import os
import shutil
import subprocess

PROJECT_DIR = "/home/user/myproject"
POCKETBASE_BINARY = os.path.join(PROJECT_DIR, "pocketbase")


def test_project_dir_exists():
    assert os.path.isdir(PROJECT_DIR), (
        f"Expected project directory to exist at {PROJECT_DIR}, but it was not found."
    )


def test_pocketbase_binary_exists():
    assert os.path.isfile(POCKETBASE_BINARY), (
        f"Expected PocketBase binary at {POCKETBASE_BINARY}, but it was not found."
    )
    assert os.access(POCKETBASE_BINARY, os.X_OK), (
        f"Expected PocketBase binary at {POCKETBASE_BINARY} to be executable."
    )


def test_pocketbase_version_is_v0_31_0():
    result = subprocess.run(
        [POCKETBASE_BINARY, "--version"],
        capture_output=True,
        text=True,
        cwd=PROJECT_DIR,
        timeout=30,
    )
    combined = (result.stdout or "") + (result.stderr or "")
    assert "0.31.0" in combined, (
        "Expected PocketBase binary to report version 0.31.0, "
        f"but got: {combined.strip()!r}"
    )


def test_curl_available():
    assert shutil.which("curl") is not None, (
        "curl binary is required for verification but was not found in PATH."
    )


def test_jq_available():
    assert shutil.which("jq") is not None, (
        "jq binary is required for verification but was not found in PATH."
    )


def test_no_preexisting_pb_data():
    pb_data_path = os.path.join(PROJECT_DIR, "pb_data")
    assert not os.path.exists(pb_data_path), (
        f"Expected no pre-existing PocketBase data directory at {pb_data_path}, "
        "but it already exists. The initial environment must start clean."
    )


def test_no_preexisting_setup_script():
    setup_script = os.path.join(PROJECT_DIR, "setup.sh")
    assert not os.path.exists(setup_script), (
        f"Expected no pre-existing setup.sh at {setup_script}; "
        "the executor is responsible for creating it."
    )


def test_port_8090_is_free():
    # Try to find any process listening on 8090; we use ss or netstat as best-effort.
    # The test passes if no listener is reported.
    for cmd in (["ss", "-ltn"], ["netstat", "-ltn"]):
        if shutil.which(cmd[0]) is None:
            continue
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        output = result.stdout or ""
        assert ":8090" not in output, (
            f"Expected no listener on port 8090 in the initial state, "
            f"but {cmd[0]} reports one:\n{output}"
        )
        return
    # If neither ss nor netstat exists, skip silently — the final state test
    # will still verify the server starts.
