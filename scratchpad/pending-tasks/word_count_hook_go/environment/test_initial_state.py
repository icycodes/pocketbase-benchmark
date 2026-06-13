import os
import shutil
import subprocess

PROJECT_DIR = "/home/user/myproject"


def test_go_binary_available():
    """The Go toolchain is required to build the PocketBase application."""
    assert shutil.which("go") is not None, "go binary not found in PATH."


def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} does not exist."


def test_go_mod_exists_and_pins_pocketbase():
    go_mod_path = os.path.join(PROJECT_DIR, "go.mod")
    assert os.path.isfile(go_mod_path), f"go.mod not found at {go_mod_path}."
    with open(go_mod_path) as f:
        content = f.read()
    assert "github.com/pocketbase/pocketbase" in content, (
        "go.mod must declare a dependency on github.com/pocketbase/pocketbase."
    )
    assert "v0.31.0" in content, (
        "go.mod must pin the PocketBase dependency to v0.31.0."
    )


def test_main_go_exists():
    main_go_path = os.path.join(PROJECT_DIR, "main.go")
    assert os.path.isfile(main_go_path), f"main.go not found at {main_go_path}."


def test_migrations_package_exists():
    migrations_dir = os.path.join(PROJECT_DIR, "migrations")
    assert os.path.isdir(migrations_dir), (
        f"Migrations directory {migrations_dir} must be present in the starter project."
    )
    go_files = [name for name in os.listdir(migrations_dir) if name.endswith(".go")]
    assert len(go_files) >= 1, (
        f"Expected at least one .go migration file inside {migrations_dir}."
    )


def test_go_mod_dependencies_pre_downloaded():
    """The agent must be able to build offline-like; verify the module graph is resolvable."""
    result = subprocess.run(
        ["go", "list", "-m", "github.com/pocketbase/pocketbase"],
        capture_output=True,
        text=True,
        cwd=PROJECT_DIR,
    )
    assert result.returncode == 0, (
        f"'go list -m github.com/pocketbase/pocketbase' failed in {PROJECT_DIR}: {result.stderr}"
    )
    assert "v0.31.0" in result.stdout, (
        f"PocketBase module version must resolve to v0.31.0 (got: {result.stdout.strip()})."
    )
