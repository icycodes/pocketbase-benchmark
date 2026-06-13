import os
import subprocess

import pytest

PROJECT_DIR = "/home/user/myproject"
POCKETBASE_BINARY = os.path.join(PROJECT_DIR, "pocketbase")


def test_project_dir_exists():
    assert os.path.isdir(PROJECT_DIR), (
        f"Project directory {PROJECT_DIR} does not exist."
    )


def test_pocketbase_binary_exists():
    assert os.path.isfile(POCKETBASE_BINARY), (
        f"PocketBase binary not found at {POCKETBASE_BINARY}."
    )
    assert os.access(POCKETBASE_BINARY, os.X_OK), (
        f"PocketBase binary at {POCKETBASE_BINARY} is not executable."
    )


def test_pocketbase_version():
    result = subprocess.run(
        [POCKETBASE_BINARY, "--version"],
        capture_output=True,
        text=True,
        cwd=PROJECT_DIR,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"`pocketbase --version` failed with stderr: {result.stderr}"
    )
    combined = (result.stdout or "") + (result.stderr or "")
    assert "0.31.0" in combined, (
        "Expected PocketBase v0.31.0 to be installed, got: "
        f"{combined.strip()!r}"
    )


def test_pb_data_dir_initialized():
    # An initial superuser is created during the image build, which
    # implicitly initializes the pb_data directory.
    pb_data = os.path.join(PROJECT_DIR, "pb_data")
    assert os.path.isdir(pb_data), (
        f"Expected PocketBase data directory {pb_data} to be initialized."
    )


def test_superuser_env_vars_present():
    assert os.environ.get("PB_SUPERUSER_EMAIL"), (
        "Environment variable PB_SUPERUSER_EMAIL is required for verification."
    )
    assert os.environ.get("PB_SUPERUSER_PASSWORD"), (
        "Environment variable PB_SUPERUSER_PASSWORD is required for verification."
    )


def test_zealt_run_id_present():
    assert os.environ.get("ZEALT_RUN_ID"), (
        "Environment variable ZEALT_RUN_ID is required to isolate parallel test runs."
    )
