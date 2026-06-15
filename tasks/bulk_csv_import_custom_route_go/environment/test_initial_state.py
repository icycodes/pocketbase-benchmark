import os
import shutil
import subprocess

PROJECT_DIR = "/home/user/myproject"
PB_SEED_DIR = "/opt/pb_seed"


def test_go_binary_available():
    assert shutil.which("go") is not None, "Go toolchain binary 'go' not found in PATH."


def test_go_version_is_supported():
    result = subprocess.run(
        ["go", "version"], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, (
        f"`go version` failed with exit code {result.returncode}: {result.stderr}"
    )
    output = result.stdout.strip()
    # Expected output looks like: "go version go1.22.x linux/amd64"
    assert "go version go1." in output, (
        f"Unexpected `go version` output: {output!r}"
    )


def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR), (
        f"Project directory {PROJECT_DIR} does not exist."
    )


def test_pb_seed_dir_exists():
    # The task.json setup expects a seeded pb_data directory under /opt/pb_seed
    # so that the superuser credentials are already present before the executor
    # builds and runs the Go binary.
    assert os.path.isdir(PB_SEED_DIR), (
        f"Seeded PocketBase directory {PB_SEED_DIR} does not exist."
    )
    assert os.path.isdir(os.path.join(PB_SEED_DIR, "pb_data")), (
        f"Seeded pb_data directory {PB_SEED_DIR}/pb_data does not exist."
    )
    assert os.path.isfile(os.path.join(PB_SEED_DIR, "pb_data", "data.db")), (
        f"Seeded SQLite database {PB_SEED_DIR}/pb_data/data.db does not exist."
    )


def test_superuser_credentials_env_present():
    assert os.environ.get("PB_SUPERUSER_EMAIL"), (
        "PB_SUPERUSER_EMAIL environment variable is not set."
    )
    assert os.environ.get("PB_SUPERUSER_PASSWORD"), (
        "PB_SUPERUSER_PASSWORD environment variable is not set."
    )


def test_pocketbase_go_module_cached():
    # The PocketBase v0.31.0 Go module should be pre-downloaded into the
    # Go module cache so that the executor can build offline-friendly.
    gopath = (
        subprocess.run(
            ["go", "env", "GOMODCACHE"],
            capture_output=True,
            text=True,
            check=True,
        )
        .stdout.strip()
    )
    assert gopath, "`go env GOMODCACHE` returned an empty value."
    pb_module_dir = os.path.join(gopath, "github.com", "pocketbase")
    assert os.path.isdir(pb_module_dir), (
        f"PocketBase Go module cache directory not found at {pb_module_dir}."
    )
