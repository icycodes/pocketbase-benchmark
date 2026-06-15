import os
import shutil
import subprocess

PROJECT_DIR = "/home/user/myproject"


def test_go_toolchain_available():
    assert shutil.which("go") is not None, (
        "Go toolchain (`go`) is not available in PATH. The task requires building "
        "a custom PocketBase binary."
    )


def test_go_version_supports_pocketbase():
    result = subprocess.run(
        ["go", "version"], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, (
        f"`go version` failed: stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "go1." in result.stdout, (
        f"Unexpected `go version` output: {result.stdout!r}"
    )


def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR), (
        f"Expected project directory {PROJECT_DIR} to exist before evaluation."
    )


def test_pocketbase_module_preinstalled_in_module_cache():
    # The Dockerfile is expected to pre-fetch the v0.31.0 module so the executor
    # does not need network access at build time. We just verify the module cache
    # contains the expected version directory.
    gopath = (
        subprocess.run(
            ["go", "env", "GOPATH"], capture_output=True, text=True, check=False
        ).stdout.strip()
        or os.path.expanduser("~/go")
    )
    module_cache = os.path.join(gopath, "pkg", "mod", "github.com", "pocketbase")
    assert os.path.isdir(module_cache), (
        f"Expected pocketbase module cache directory at {module_cache}. "
        "The Dockerfile should pre-fetch github.com/pocketbase/pocketbase@v0.31.0."
    )
    entries = os.listdir(module_cache)
    has_v31 = any("pocketbase@v0.31.0" in e for e in entries)
    assert has_v31, (
        f"Expected pocketbase@v0.31.0 in module cache {module_cache}, found: {entries}"
    )


def test_superuser_bootstrap_env_vars_present():
    assert os.environ.get("PB_SUPERUSER_EMAIL"), (
        "PB_SUPERUSER_EMAIL env var is not set; superuser bootstrap will not work."
    )
    assert os.environ.get("PB_SUPERUSER_PASSWORD"), (
        "PB_SUPERUSER_PASSWORD env var is not set; superuser bootstrap will not work."
    )
