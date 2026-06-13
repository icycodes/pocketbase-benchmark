import os
import shutil
import subprocess


PROJECT_DIR = "/home/user/myproject"


def test_go_toolchain_available():
    assert shutil.which("go") is not None, "Go toolchain is not available in PATH."


def test_curl_available():
    # The verification plan exercises the running server via curl.
    assert shutil.which("curl") is not None, "curl is required for the verification plan but is not in PATH."


def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR), f"Expected project directory at {PROJECT_DIR}."


def test_go_module_exists():
    go_mod = os.path.join(PROJECT_DIR, "go.mod")
    assert os.path.isfile(go_mod), f"Expected go.mod at {go_mod}."
    with open(go_mod) as f:
        content = f.read()
    assert "github.com/pocketbase/pocketbase" in content, (
        "go.mod must declare a dependency on github.com/pocketbase/pocketbase."
    )


def test_main_go_skeleton_present():
    main_go = os.path.join(PROJECT_DIR, "main.go")
    assert os.path.isfile(main_go), f"Expected initial main.go skeleton at {main_go}."
    with open(main_go) as f:
        content = f.read()
    assert "pocketbase.New()" in content, (
        "Initial main.go must instantiate PocketBase via pocketbase.New()."
    )
    assert "app.Start()" in content, (
        "Initial main.go must call app.Start() to start the server."
    )


def test_migrations_package_present():
    migrations_dir = os.path.join(PROJECT_DIR, "migrations")
    assert os.path.isdir(migrations_dir), (
        f"Expected pre-existing migrations directory at {migrations_dir}."
    )
    go_files = [f for f in os.listdir(migrations_dir) if f.endswith(".go")]
    assert go_files, "migrations/ should contain at least one .go migration file."


def test_pocketbase_dependency_vendored_or_cached():
    # Ensure that `go build` will not have to fetch dependencies from the network during evaluation.
    result = subprocess.run(
        ["go", "build", "-o", "/tmp/pb_initial_state_check", "."],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, (
        "Initial project must build cleanly with `go build .` before the task starts. "
        f"stderr=\n{result.stderr}"
    )
    assert os.path.isfile("/tmp/pb_initial_state_check"), (
        "Expected the build artifact to be produced at /tmp/pb_initial_state_check."
    )
    try:
        os.remove("/tmp/pb_initial_state_check")
    except OSError:
        pass


def test_slug_hook_not_yet_implemented():
    # The slug hook must not already be implemented in the initial state.
    main_go = os.path.join(PROJECT_DIR, "main.go")
    with open(main_go) as f:
        content = f.read()
    assert "OnRecordCreateRequest" not in content, (
        "Initial main.go must NOT already register the OnRecordCreateRequest hook; "
        "that work is the responsibility of the executor."
    )
