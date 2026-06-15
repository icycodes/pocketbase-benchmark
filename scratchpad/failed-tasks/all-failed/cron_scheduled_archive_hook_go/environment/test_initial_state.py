import os
import re
import shutil

import pytest

PROJECT_DIR = "/home/user/myproject"
GO_MOD = os.path.join(PROJECT_DIR, "go.mod")
MAIN_GO = os.path.join(PROJECT_DIR, "main.go")


def test_go_toolchain_available():
    assert shutil.which("go") is not None, (
        "The Go toolchain is required but the `go` binary was not found in PATH."
    )


def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR), (
        f"Expected the project skeleton directory to exist at {PROJECT_DIR}."
    )


def test_go_mod_exists():
    assert os.path.isfile(GO_MOD), (
        f"Expected a Go module manifest at {GO_MOD} to seed the Go project skeleton."
    )


def test_go_mod_pins_pocketbase_v0_31_0():
    with open(GO_MOD, "r", encoding="utf-8") as f:
        content = f.read()
    assert re.search(
        r"github\.com/pocketbase/pocketbase\s+v0\.31\.0", content
    ), (
        "Expected go.mod to require github.com/pocketbase/pocketbase at exactly v0.31.0; "
        f"got:\n{content}"
    )


def test_main_go_skeleton_exists():
    assert os.path.isfile(MAIN_GO), (
        f"Expected a starter Go entrypoint at {MAIN_GO} (the project skeleton)."
    )


def test_main_go_imports_pocketbase():
    with open(MAIN_GO, "r", encoding="utf-8") as f:
        content = f.read()
    assert "github.com/pocketbase/pocketbase" in content, (
        "Expected the starter main.go to already import github.com/pocketbase/pocketbase "
        "so the executor only has to add the cron/archive logic."
    )


def test_pocketbase_module_prefetched():
    """
    The Dockerfile is expected to pre-fetch the PocketBase Go module into the
    module cache so the executor can build offline. We assert that the module
    cache contains the pinned version.
    """
    gopath = os.environ.get("GOPATH") or os.path.expanduser("~/go")
    cache_root = os.path.join(gopath, "pkg", "mod", "cache", "download",
                              "github.com", "pocketbase", "pocketbase", "@v")
    assert os.path.isdir(cache_root), (
        f"Expected the Go module download cache for pocketbase at {cache_root}."
    )
    entries = os.listdir(cache_root)
    assert any(name.startswith("v0.31.0") for name in entries), (
        "Expected pocketbase v0.31.0 to be present in the Go module download "
        f"cache at {cache_root}; found: {entries}"
    )
