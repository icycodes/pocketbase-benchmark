import json
import os
import socket
import subprocess
import time

import pytest
import requests
from xprocess import ProcessStarter

PROJECT_DIR = "/home/user/myproject"
BASE_URL = "http://127.0.0.1:8090"
USER_EMAIL = "user@example.com"
USER_PASSWORD = "testpass1234"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "adminpass1234"


def _wait_port(host: str, port: int, timeout: float = 60.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            if s.connect_ex((host, port)) == 0:
                return True
        time.sleep(0.5)
    return False


def _superuser_token() -> str:
    r = requests.post(
        f"{BASE_URL}/api/collections/_superusers/auth-with-password",
        json={"identity": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=30,
    )
    assert r.status_code == 200, (
        f"Failed to authenticate as superuser: {r.status_code} {r.text}"
    )
    return r.json()["token"]


def _delete_all_records(collection: str, token: str) -> None:
    headers = {"Authorization": token}
    page = 1
    while True:
        r = requests.get(
            f"{BASE_URL}/api/collections/{collection}/records",
            params={"perPage": 200, "page": page},
            headers=headers,
            timeout=30,
        )
        assert r.status_code == 200, (
            f"Failed to list '{collection}' for cleanup: {r.status_code} {r.text}"
        )
        items = r.json().get("items", [])
        if not items:
            break
        for it in items:
            rid = it["id"]
            d = requests.delete(
                f"{BASE_URL}/api/collections/{collection}/records/{rid}",
                headers=headers,
                timeout=30,
            )
            assert d.status_code in (200, 204), (
                f"Failed to delete {collection}/{rid}: {d.status_code} {d.text}"
            )
        if len(items) < 200:
            break
        page += 1


@pytest.fixture(scope="session", autouse=True)
def app_server(xprocess):
    build = subprocess.run(
        ["go", "build", "-o", "app", "."],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert build.returncode == 0, (
        f"Failed to build the Go PocketBase app: {build.stderr}"
    )

    class Starter(ProcessStarter):
        name = "pb_app"
        args = ["./app", "serve", "--http=0.0.0.0:8090"]
        env = os.environ.copy()
        popen_kwargs = {"cwd": PROJECT_DIR, "text": True}
        timeout = 120
        terminate_on_interrupt = True

        def startup_check(self):
            return _wait_port("127.0.0.1", 8090, timeout=2.0)

    xprocess.ensure(Starter.name, Starter)

    assert _wait_port("127.0.0.1", 8090, timeout=60), (
        "PocketBase server did not become ready on port 8090."
    )

    # Reset audit_log and posts to a clean state before the scenario.
    token = _superuser_token()
    _delete_all_records("audit_log", token)
    _delete_all_records("posts", token)

    yield

    info = xprocess.getinfo(Starter.name)
    info.terminate()


@pytest.fixture(scope="session")
def scenario_state(app_server):
    # 1. Authenticate as the regular user.
    auth = requests.post(
        f"{BASE_URL}/api/collections/users/auth-with-password",
        json={"identity": USER_EMAIL, "password": USER_PASSWORD},
        timeout=30,
    )
    assert auth.status_code == 200, (
        f"User authentication failed: {auth.status_code} {auth.text}"
    )
    auth_body = auth.json()
    user_token = auth_body["token"]
    user_id = auth_body["record"]["id"]
    user_headers = {"Authorization": user_token}

    # 2. Create a posts record with title "Original Title".
    create = requests.post(
        f"{BASE_URL}/api/collections/posts/records",
        json={"title": "Original Title"},
        headers=user_headers,
        timeout=30,
    )
    assert create.status_code in (200, 201), (
        f"Failed to create posts record: {create.status_code} {create.text}"
    )
    post_id = create.json()["id"]

    # 3. Update the post changing only the title to "Updated Title".
    update = requests.patch(
        f"{BASE_URL}/api/collections/posts/records/{post_id}",
        json={"title": "Updated Title"},
        headers=user_headers,
        timeout=30,
    )
    assert update.status_code == 200, (
        f"Failed to update posts record: {update.status_code} {update.text}"
    )

    # 4. Delete the post.
    delete = requests.delete(
        f"{BASE_URL}/api/collections/posts/records/{post_id}",
        headers=user_headers,
        timeout=30,
    )
    assert delete.status_code in (200, 204), (
        f"Failed to delete posts record: {delete.status_code} {delete.text}"
    )

    # Give the server a moment to persist audit rows for the delete event.
    time.sleep(1.0)

    return {"user_id": user_id, "post_id": post_id}


def _fetch_audit_rows_for_post(post_id: str):
    token = _superuser_token()
    r = requests.get(
        f"{BASE_URL}/api/collections/audit_log/records",
        params={
            "filter": f'record="{post_id}"',
            "sort": "created",
            "perPage": 200,
        },
        headers={"Authorization": token},
        timeout=30,
    )
    assert r.status_code == 200, (
        f"Failed to query audit_log: {r.status_code} {r.text}"
    )
    return r.json().get("items", [])


def _parse_diff(value):
    if value is None or value == "":
        return {}
    if isinstance(value, (dict, list)):
        return value
    return json.loads(value)


def test_audit_log_has_exactly_three_rows_for_post(scenario_state):
    rows = _fetch_audit_rows_for_post(scenario_state["post_id"])
    assert len(rows) == 3, (
        f"Expected exactly 3 audit_log rows for the posts record, got {len(rows)}: {rows}"
    )


def test_audit_log_actions_in_order_create_update_delete(scenario_state):
    rows = _fetch_audit_rows_for_post(scenario_state["post_id"])
    actions = [row.get("action") for row in rows]
    assert actions == ["create", "update", "delete"], (
        f"Expected audit_log actions to be ['create', 'update', 'delete'] in order, got {actions}."
    )


def test_audit_log_rows_reference_post_id_and_collection(scenario_state):
    rows = _fetch_audit_rows_for_post(scenario_state["post_id"])
    for row in rows:
        assert row.get("collection") == "posts", (
            f"audit_log row has wrong collection: {row}"
        )
        assert row.get("record") == scenario_state["post_id"], (
            f"audit_log row has wrong record id: {row}"
        )


def test_audit_log_rows_reference_actor_user_id(scenario_state):
    rows = _fetch_audit_rows_for_post(scenario_state["post_id"])
    for row in rows:
        assert row.get("actor") == scenario_state["user_id"], (
            f"audit_log row has wrong actor: expected {scenario_state['user_id']}, got {row.get('actor')}"
        )


def test_create_and_delete_rows_have_empty_diff(scenario_state):
    rows = _fetch_audit_rows_for_post(scenario_state["post_id"])
    by_action = {row["action"]: row for row in rows}
    create_diff = _parse_diff(by_action["create"].get("diff"))
    delete_diff = _parse_diff(by_action["delete"].get("diff"))
    assert create_diff == {}, (
        f"Expected empty diff for create row, got {create_diff!r}."
    )
    assert delete_diff == {}, (
        f"Expected empty diff for delete row, got {delete_diff!r}."
    )


def test_update_row_diff_matches_title_change_exactly(scenario_state):
    rows = _fetch_audit_rows_for_post(scenario_state["post_id"])
    by_action = {row["action"]: row for row in rows}
    diff = _parse_diff(by_action["update"].get("diff"))
    expected = {"title": {"old": "Original Title", "new": "Updated Title"}}
    assert diff == expected, (
        f"Expected update diff to be exactly {expected!r}, got {diff!r}."
    )


def test_no_audit_rows_reference_audit_log_itself(app_server):
    token = _superuser_token()
    r = requests.get(
        f"{BASE_URL}/api/collections/audit_log/records",
        params={"filter": 'collection="audit_log"', "perPage": 1},
        headers={"Authorization": token},
        timeout=30,
    )
    assert r.status_code == 200, (
        f"Failed to query audit_log for self-references: {r.status_code} {r.text}"
    )
    total = r.json().get("totalItems", 0)
    assert total == 0, (
        f"Found {total} audit_log rows where collection='audit_log'; "
        "the audit_log collection must be excluded from auditing."
    )
