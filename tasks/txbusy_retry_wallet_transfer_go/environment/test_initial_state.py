import os
import re
import shutil
import sqlite3

import pytest

PROJECT_DIR = "/home/user/myproject"
GO_MOD = os.path.join(PROJECT_DIR, "go.mod")
MAIN_GO = os.path.join(PROJECT_DIR, "main.go")
DATA_DB = os.path.join(PROJECT_DIR, "pb_data", "data.db")


def test_go_toolchain_available():
    assert shutil.which("go") is not None, "Go toolchain not found in PATH."


def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} does not exist."


def test_go_mod_pins_pocketbase_v0_31_0():
    assert os.path.isfile(GO_MOD), f"Expected go.mod at {GO_MOD}."
    with open(GO_MOD) as f:
        content = f.read()
    assert "github.com/pocketbase/pocketbase" in content, (
        "go.mod must depend on github.com/pocketbase/pocketbase."
    )
    assert re.search(r"github\.com/pocketbase/pocketbase\s+v0\.31\.0", content), (
        "go.mod must pin github.com/pocketbase/pocketbase to v0.31.0."
    )


def test_starter_main_go_exists():
    assert os.path.isfile(MAIN_GO), (
        f"Expected starter main.go at {MAIN_GO} to embed PocketBase."
    )


def test_pb_data_database_exists():
    assert os.path.isfile(DATA_DB), (
        f"Expected pre-seeded PocketBase database at {DATA_DB}."
    )


def _connect_db():
    if not os.path.isfile(DATA_DB):
        pytest.skip(f"{DATA_DB} not present; cannot inspect seeded state.")
    return sqlite3.connect(f"file:{DATA_DB}?mode=ro", uri=True)


def test_wallets_collection_seeded_with_a_and_b():
    conn = _connect_db()
    try:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='wallets'"
        )
        assert cur.fetchone() is not None, (
            "wallets table is missing from the seeded PocketBase database."
        )

        balances = sorted(
            float(row[0])
            for row in conn.execute("SELECT balance FROM wallets").fetchall()
        )
        assert balances == [0.0, 100.0], (
            f"Expected exactly two seeded wallets with balances 0 and 100, got {balances}."
        )
    finally:
        conn.close()


def test_transfers_collection_exists_and_empty():
    conn = _connect_db()
    try:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='transfers'"
        )
        assert cur.fetchone() is not None, (
            "transfers table is missing from the seeded PocketBase database."
        )
        count = conn.execute("SELECT COUNT(*) FROM transfers").fetchone()[0]
        assert count == 0, (
            f"Expected the transfers audit table to start empty, got {count} rows."
        )
    finally:
        conn.close()


def test_users_auth_collection_has_a_test_user():
    conn = _connect_db()
    try:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        )
        assert cur.fetchone() is not None, (
            "users auth collection is missing from the seeded PocketBase database."
        )
        count = conn.execute(
            "SELECT COUNT(*) FROM users WHERE email='tester@example.com'"
        ).fetchone()[0]
        assert count == 1, (
            "Expected a pre-seeded test user tester@example.com in the users collection."
        )
    finally:
        conn.close()
