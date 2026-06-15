import glob
import os
import socket
import time
from typing import Any, Dict, List, Optional

import pytest
import requests
from xprocess import ProcessStarter

PROJECT_DIR = "/home/user/myproject"
MIGRATIONS_DIR = os.path.join(PROJECT_DIR, "pb_migrations")
BASE_URL = "http://127.0.0.1:8090"

PB_PORT = 8090
USER_PASSWORD = "Test123Password!"


def _run_id() -> str:
    run_id = os.environ.get("ZEALT_RUN_ID")
    assert run_id, "ZEALT_RUN_ID environment variable is required."
    return run_id


def _superuser_email() -> str:
    email = os.environ.get("PB_SUPERUSER_EMAIL")
    assert email, "PB_SUPERUSER_EMAIL must be set in the environment."
    return email


def _superuser_password() -> str:
    pw = os.environ.get("PB_SUPERUSER_PASSWORD")
    assert pw, "PB_SUPERUSER_PASSWORD must be set in the environment."
    return pw


def _auth(token: Optional[str]) -> Dict[str, str]:
    if token is None:
        return {}
    return {"Authorization": token}


def _login_superuser() -> str:
    resp = requests.post(
        f"{BASE_URL}/api/collections/_superusers/auth-with-password",
        json={"identity": _superuser_email(), "password": _superuser_password()},
        timeout=15,
    )
    assert resp.status_code == 200, (
        f"Failed to authenticate as superuser: HTTP {resp.status_code} {resp.text}"
    )
    token = resp.json().get("token")
    assert token, "Superuser auth response missing token."
    return token


def _register_and_login_user(email: str) -> Dict[str, str]:
    """Create a new user record and return {id, email, token}."""
    create_resp = requests.post(
        f"{BASE_URL}/api/collections/users/records",
        json={
            "email": email,
            "password": USER_PASSWORD,
            "passwordConfirm": USER_PASSWORD,
        },
        timeout=15,
    )
    assert create_resp.status_code == 200, (
        f"Failed to register user {email!r}: HTTP {create_resp.status_code} {create_resp.text}"
    )
    user_id = create_resp.json().get("id")
    assert user_id, f"User create response missing id for {email!r}."

    auth_resp = requests.post(
        f"{BASE_URL}/api/collections/users/auth-with-password",
        json={"identity": email, "password": USER_PASSWORD},
        timeout=15,
    )
    assert auth_resp.status_code == 200, (
        f"Failed to log in user {email!r}: HTTP {auth_resp.status_code} {auth_resp.text}"
    )
    token = auth_resp.json().get("token")
    assert token, f"Login response for {email!r} missing token."
    return {"id": user_id, "email": email, "token": token}


@pytest.fixture(scope="session")
def start_pocketbase(xprocess):
    class Starter(ProcessStarter):
        name = "start_pocketbase"
        args = ["./pocketbase", "serve", "--http=0.0.0.0:8090"]
        env = os.environ.copy()
        popen_kwargs = {
            "cwd": PROJECT_DIR,
            "text": True,
        }
        timeout = 60
        terminate_on_interrupt = True

        def startup_check(self):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(2)
                    if s.connect_ex(("127.0.0.1", PB_PORT)) != 0:
                        return False
                resp = requests.get(f"{BASE_URL}/api/health", timeout=5)
                return resp.status_code == 200
            except Exception:
                return False

    xprocess.ensure(Starter.name, Starter)

    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            r = requests.get(f"{BASE_URL}/api/health", timeout=2)
            if r.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(0.5)

    yield

    info = xprocess.getinfo(Starter.name)
    info.terminate()


@pytest.fixture(scope="session")
def seeded_state(start_pocketbase) -> Dict[str, Any]:
    """Set up superuser auth, three users, and a project membership for testing."""
    run_id = _run_id()
    superuser_token = _login_superuser()

    member_a = _register_and_login_user(f"member-a-{run_id}@example.com")
    member_b = _register_and_login_user(f"member-b-{run_id}@example.com")
    outsider = _register_and_login_user(f"outsider-{run_id}@example.com")

    project_resp = requests.post(
        f"{BASE_URL}/api/collections/projects/records",
        json={
            "name": f"harbor-proj-{run_id}",
            "members": [member_a["id"], member_b["id"]],
        },
        headers=_auth(superuser_token),
        timeout=15,
    )
    assert project_resp.status_code == 200, (
        "Superuser failed to seed project. The 'projects' collection may be missing or have an unexpected schema. "
        f"Got HTTP {project_resp.status_code}: {project_resp.text}"
    )
    project = project_resp.json()
    project_id = project.get("id")
    assert project_id, f"Seeded project response missing id: {project}"

    return {
        "run_id": run_id,
        "superuser_token": superuser_token,
        "member_a": member_a,
        "member_b": member_b,
        "outsider": outsider,
        "project_id": project_id,
    }


def test_migration_file_exists():
    """A *.js migration file must be present in pb_migrations/."""
    matches = glob.glob(os.path.join(MIGRATIONS_DIR, "*.js"))
    assert matches, (
        f"Expected at least one '*.js' migration file under {MIGRATIONS_DIR}, found none."
    )


def _find_field(fields: List[Dict[str, Any]], name: str) -> Optional[Dict[str, Any]]:
    for f in fields:
        if f.get("name") == name:
            return f
    return None


def test_projects_collection_schema(seeded_state):
    token = seeded_state["superuser_token"]
    resp = requests.get(
        f"{BASE_URL}/api/collections/projects",
        headers=_auth(token),
        timeout=15,
    )
    assert resp.status_code == 200, (
        "Superuser failed to fetch 'projects' collection schema. "
        f"Got HTTP {resp.status_code}: {resp.text}"
    )
    data = resp.json()
    assert data.get("type") == "base", (
        f"Expected 'projects' to be a base collection, got type={data.get('type')!r}."
    )
    fields = data.get("fields") or []

    name_field = _find_field(fields, "name")
    assert name_field is not None, "Expected 'name' field on 'projects' collection."
    assert name_field.get("type") == "text", (
        f"Expected 'name' field on 'projects' to be of type 'text', got {name_field.get('type')!r}."
    )
    assert name_field.get("required") is True, (
        "Expected 'name' field on 'projects' to be required."
    )

    members_field = _find_field(fields, "members")
    assert members_field is not None, "Expected 'members' field on 'projects' collection."
    assert members_field.get("type") == "relation", (
        f"Expected 'members' field on 'projects' to be of type 'relation', got {members_field.get('type')!r}."
    )
    # multi-select: either explicit > 1 or null/0 indicating unlimited
    max_select = members_field.get("maxSelect")
    assert max_select != 1, (
        f"Expected 'members' field on 'projects' to be multi-select (maxSelect != 1), got maxSelect={max_select!r}."
    )

    # Verify it points to the built-in users collection
    users_resp = requests.get(
        f"{BASE_URL}/api/collections/users",
        headers=_auth(token),
        timeout=15,
    )
    assert users_resp.status_code == 200, (
        f"Could not fetch 'users' collection schema: HTTP {users_resp.status_code} {users_resp.text}"
    )
    users_id = users_resp.json().get("id")
    assert members_field.get("collectionId") == users_id, (
        "Expected 'members' relation on 'projects' to point to the 'users' collection. "
        f"members.collectionId={members_field.get('collectionId')!r}, users.id={users_id!r}."
    )


def test_tasks_collection_schema(seeded_state):
    token = seeded_state["superuser_token"]
    resp = requests.get(
        f"{BASE_URL}/api/collections/tasks",
        headers=_auth(token),
        timeout=15,
    )
    assert resp.status_code == 200, (
        "Superuser failed to fetch 'tasks' collection schema. "
        f"Got HTTP {resp.status_code}: {resp.text}"
    )
    data = resp.json()
    assert data.get("type") == "base", (
        f"Expected 'tasks' to be a base collection, got type={data.get('type')!r}."
    )
    fields = data.get("fields") or []

    title_field = _find_field(fields, "title")
    assert title_field is not None, "Expected 'title' field on 'tasks' collection."
    assert title_field.get("type") == "text", (
        f"Expected 'title' field on 'tasks' to be of type 'text', got {title_field.get('type')!r}."
    )
    assert title_field.get("required") is True, (
        "Expected 'title' field on 'tasks' to be required."
    )

    description_field = _find_field(fields, "description")
    assert description_field is not None, "Expected 'description' field on 'tasks' collection."
    assert description_field.get("type") == "text", (
        f"Expected 'description' field on 'tasks' to be of type 'text', got {description_field.get('type')!r}."
    )

    project_field = _find_field(fields, "project")
    assert project_field is not None, "Expected 'project' field on 'tasks' collection."
    assert project_field.get("type") == "relation", (
        f"Expected 'project' field on 'tasks' to be of type 'relation', got {project_field.get('type')!r}."
    )
    assert project_field.get("required") is True, (
        "Expected 'project' field on 'tasks' to be required."
    )
    assert project_field.get("maxSelect") == 1, (
        "Expected 'project' field on 'tasks' to be a single-select relation "
        f"(maxSelect=1), got {project_field.get('maxSelect')!r}."
    )

    projects_resp = requests.get(
        f"{BASE_URL}/api/collections/projects",
        headers=_auth(token),
        timeout=15,
    )
    assert projects_resp.status_code == 200, (
        f"Could not fetch 'projects' collection schema: HTTP {projects_resp.status_code} {projects_resp.text}"
    )
    projects_id = projects_resp.json().get("id")
    assert project_field.get("collectionId") == projects_id, (
        "Expected 'project' relation on 'tasks' to point to the 'projects' collection. "
        f"project.collectionId={project_field.get('collectionId')!r}, projects.id={projects_id!r}."
    )


def test_member_can_list_and_view_project(seeded_state):
    project_id = seeded_state["project_id"]
    run_id = seeded_state["run_id"]
    expected_name = f"harbor-proj-{run_id}"

    for who in ("member_a", "member_b"):
        token = seeded_state[who]["token"]
        list_resp = requests.get(
            f"{BASE_URL}/api/collections/projects/records",
            headers=_auth(token),
            timeout=15,
        )
        assert list_resp.status_code == 200, (
            f"{who} expected to list projects (HTTP 200), got "
            f"{list_resp.status_code}: {list_resp.text}"
        )
        items = list_resp.json().get("items", [])
        ids = [it.get("id") for it in items]
        assert project_id in ids, (
            f"{who} should see project {project_id} in their list response, got ids={ids}."
        )
        names = {it.get("id"): it.get("name") for it in items}
        assert names.get(project_id) == expected_name, (
            f"Expected project name to be {expected_name!r} for {who}, got {names.get(project_id)!r}."
        )

        view_resp = requests.get(
            f"{BASE_URL}/api/collections/projects/records/{project_id}",
            headers=_auth(token),
            timeout=15,
        )
        assert view_resp.status_code == 200, (
            f"{who} should be able to view project {project_id} (HTTP 200), got "
            f"{view_resp.status_code}: {view_resp.text}"
        )
        assert view_resp.json().get("id") == project_id, (
            f"View response for {who} returned unexpected id."
        )


def test_outsider_is_blocked_from_project(seeded_state):
    token = seeded_state["outsider"]["token"]
    project_id = seeded_state["project_id"]

    list_resp = requests.get(
        f"{BASE_URL}/api/collections/projects/records",
        headers=_auth(token),
        timeout=15,
    )
    assert list_resp.status_code == 200, (
        "Outsider list of projects should respond 200 (filtered list), got "
        f"{list_resp.status_code}: {list_resp.text}"
    )
    items = list_resp.json().get("items", [])
    ids = [it.get("id") for it in items]
    assert project_id not in ids, (
        "Outsider must NOT see project they don't belong to. "
        f"Got ids={ids}, project_id={project_id}."
    )

    view_resp = requests.get(
        f"{BASE_URL}/api/collections/projects/records/{project_id}",
        headers=_auth(token),
        timeout=15,
    )
    assert view_resp.status_code == 404, (
        "Outsider direct view of a project they are not a member of must return HTTP 404, got "
        f"{view_resp.status_code}: {view_resp.text}"
    )


def test_guest_is_blocked_from_project(seeded_state):
    project_id = seeded_state["project_id"]
    view_resp = requests.get(
        f"{BASE_URL}/api/collections/projects/records/{project_id}",
        timeout=15,
    )
    assert view_resp.status_code >= 400, (
        "Guest direct view of a project must return a non-2xx response, got "
        f"{view_resp.status_code}: {view_resp.text}"
    )


def test_member_can_create_task(seeded_state):
    token = seeded_state["member_a"]["token"]
    project_id = seeded_state["project_id"]
    run_id = seeded_state["run_id"]
    title = f"task-by-a-{run_id}"

    resp = requests.post(
        f"{BASE_URL}/api/collections/tasks/records",
        json={
            "title": title,
            "description": "created by member A",
            "project": project_id,
        },
        headers=_auth(token),
        timeout=15,
    )
    assert resp.status_code == 200, (
        "memberA should be able to create a task in their own project (HTTP 200), got "
        f"{resp.status_code}: {resp.text}"
    )
    body = resp.json()
    assert body.get("title") == title, (
        f"Created task should have title {title!r}, got {body.get('title')!r}."
    )
    assert body.get("project") == project_id, (
        f"Created task should reference project {project_id!r}, got {body.get('project')!r}."
    )
    task_id = body.get("id")
    assert task_id, f"Created task response missing id: {body}"

    seeded_state["task_id"] = task_id


def test_outsider_cannot_create_task(seeded_state):
    token = seeded_state["outsider"]["token"]
    project_id = seeded_state["project_id"]
    run_id = seeded_state["run_id"]
    su_token = seeded_state["superuser_token"]
    title = f"task-by-outsider-{run_id}"

    resp = requests.post(
        f"{BASE_URL}/api/collections/tasks/records",
        json={
            "title": title,
            "description": "should be rejected",
            "project": project_id,
        },
        headers=_auth(token),
        timeout=15,
    )
    assert resp.status_code >= 400, (
        "Outsider must NOT be able to create a task in a project they don't belong to. "
        f"Got HTTP {resp.status_code}: {resp.text}"
    )

    check_resp = requests.get(
        f"{BASE_URL}/api/collections/tasks/records",
        params={"filter": f'(title="{title}")'},
        headers=_auth(su_token),
        timeout=15,
    )
    assert check_resp.status_code == 200, (
        "Superuser list of tasks should respond 200, got "
        f"{check_resp.status_code}: {check_resp.text}"
    )
    total = check_resp.json().get("totalItems")
    assert total == 0, (
        "Outsider's rejected task creation must not have persisted any row. "
        f"Found totalItems={total} for title={title!r}."
    )


def test_member_can_list_and_view_tasks(seeded_state):
    task_id = seeded_state.get("task_id")
    assert task_id, "task_id missing from seeded_state; predecessor test must have failed."
    project_id = seeded_state["project_id"]
    token = seeded_state["member_b"]["token"]

    list_resp = requests.get(
        f"{BASE_URL}/api/collections/tasks/records",
        headers=_auth(token),
        timeout=15,
    )
    assert list_resp.status_code == 200, (
        f"memberB expected to list tasks (HTTP 200), got {list_resp.status_code}: {list_resp.text}"
    )
    items = list_resp.json().get("items", [])
    ids = [it.get("id") for it in items]
    assert task_id in ids, (
        f"memberB should see task {task_id} in their list response. Got ids={ids}."
    )

    view_resp = requests.get(
        f"{BASE_URL}/api/collections/tasks/records/{task_id}",
        headers=_auth(token),
        timeout=15,
    )
    assert view_resp.status_code == 200, (
        f"memberB should be able to view task {task_id} (HTTP 200), got "
        f"{view_resp.status_code}: {view_resp.text}"
    )
    body = view_resp.json()
    assert body.get("id") == task_id, "View response returned unexpected id."
    assert body.get("project") == project_id, (
        f"View response should reference project {project_id!r}, got {body.get('project')!r}."
    )


def test_outsider_cannot_list_or_view_tasks(seeded_state):
    task_id = seeded_state.get("task_id")
    assert task_id, "task_id missing from seeded_state; predecessor test must have failed."
    token = seeded_state["outsider"]["token"]

    list_resp = requests.get(
        f"{BASE_URL}/api/collections/tasks/records",
        headers=_auth(token),
        timeout=15,
    )
    assert list_resp.status_code == 200, (
        "Outsider list of tasks should respond 200 (filtered list), got "
        f"{list_resp.status_code}: {list_resp.text}"
    )
    items = list_resp.json().get("items", [])
    ids = [it.get("id") for it in items]
    assert task_id not in ids, (
        "Outsider must NOT see tasks they don't belong to. "
        f"Got ids={ids}, task_id={task_id}."
    )

    view_resp = requests.get(
        f"{BASE_URL}/api/collections/tasks/records/{task_id}",
        headers=_auth(token),
        timeout=15,
    )
    assert view_resp.status_code == 404, (
        "Outsider direct view of a task they are not allowed to see must return HTTP 404, got "
        f"{view_resp.status_code}: {view_resp.text}"
    )


def test_member_can_update_and_delete_task(seeded_state):
    task_id = seeded_state.get("task_id")
    assert task_id, "task_id missing from seeded_state; predecessor test must have failed."
    token = seeded_state["member_a"]["token"]
    su_token = seeded_state["superuser_token"]

    patch_resp = requests.patch(
        f"{BASE_URL}/api/collections/tasks/records/{task_id}",
        json={"description": "updated by A"},
        headers=_auth(token),
        timeout=15,
    )
    assert patch_resp.status_code == 200, (
        "memberA should be able to update their own task (HTTP 200), got "
        f"{patch_resp.status_code}: {patch_resp.text}"
    )
    assert patch_resp.json().get("description") == "updated by A", (
        f"Update did not persist 'description'. Got {patch_resp.json().get('description')!r}."
    )

    del_resp = requests.delete(
        f"{BASE_URL}/api/collections/tasks/records/{task_id}",
        headers=_auth(token),
        timeout=15,
    )
    assert del_resp.status_code == 204, (
        "memberA should be able to delete their own task (HTTP 204), got "
        f"{del_resp.status_code}: {del_resp.text}"
    )

    after_resp = requests.get(
        f"{BASE_URL}/api/collections/tasks/records/{task_id}",
        headers=_auth(su_token),
        timeout=15,
    )
    assert after_resp.status_code == 404, (
        "After deletion, superuser GET of the task should return HTTP 404, got "
        f"{after_resp.status_code}: {after_resp.text}"
    )


def test_outsider_cannot_modify_others_task(seeded_state):
    token = seeded_state["outsider"]["token"]
    su_token = seeded_state["superuser_token"]
    project_id = seeded_state["project_id"]
    run_id = seeded_state["run_id"]
    victim_title = f"task-victim-{run_id}"

    # Superuser seeds a victim task that the outsider should not be able to touch.
    create_resp = requests.post(
        f"{BASE_URL}/api/collections/tasks/records",
        json={"title": victim_title, "project": project_id},
        headers=_auth(su_token),
        timeout=15,
    )
    assert create_resp.status_code == 200, (
        "Superuser seeding the victim task should succeed (HTTP 200), got "
        f"{create_resp.status_code}: {create_resp.text}"
    )
    victim_task_id = create_resp.json().get("id")
    assert victim_task_id, f"Victim task creation response missing id: {create_resp.json()}"

    patch_resp = requests.patch(
        f"{BASE_URL}/api/collections/tasks/records/{victim_task_id}",
        json={"description": "hacked"},
        headers=_auth(token),
        timeout=15,
    )
    assert patch_resp.status_code >= 400, (
        "Outsider must NOT be able to PATCH a task they don't belong to. "
        f"Got HTTP {patch_resp.status_code}: {patch_resp.text}"
    )

    del_resp = requests.delete(
        f"{BASE_URL}/api/collections/tasks/records/{victim_task_id}",
        headers=_auth(token),
        timeout=15,
    )
    assert del_resp.status_code >= 400, (
        "Outsider must NOT be able to DELETE a task they don't belong to. "
        f"Got HTTP {del_resp.status_code}: {del_resp.text}"
    )

    # Verify the task still exists and the description was NOT changed.
    after_resp = requests.get(
        f"{BASE_URL}/api/collections/tasks/records/{victim_task_id}",
        headers=_auth(su_token),
        timeout=15,
    )
    assert after_resp.status_code == 200, (
        "Victim task should still exist after outsider's failed delete (superuser GET should be HTTP 200), got "
        f"{after_resp.status_code}: {after_resp.text}"
    )
    body = after_resp.json()
    assert body.get("description", "") != "hacked", (
        "Outsider's failed PATCH must NOT have mutated the victim task description. "
        f"Got description={body.get('description')!r}."
    )

    seeded_state["victim_task_id"] = victim_task_id


def test_superuser_retains_full_access(seeded_state):
    su_token = seeded_state["superuser_token"]
    project_id = seeded_state["project_id"]
    victim_task_id = seeded_state.get("victim_task_id")
    assert victim_task_id, (
        "victim_task_id missing from seeded_state; predecessor test must have failed."
    )

    proj_list = requests.get(
        f"{BASE_URL}/api/collections/projects/records",
        headers=_auth(su_token),
        timeout=15,
    )
    assert proj_list.status_code == 200, (
        f"Superuser project list expected HTTP 200, got {proj_list.status_code}: {proj_list.text}"
    )
    proj_ids = [it.get("id") for it in proj_list.json().get("items", [])]
    assert project_id in proj_ids, (
        f"Superuser should see project {project_id} in their list. Got ids={proj_ids}."
    )

    task_list = requests.get(
        f"{BASE_URL}/api/collections/tasks/records",
        headers=_auth(su_token),
        timeout=15,
    )
    assert task_list.status_code == 200, (
        f"Superuser task list expected HTTP 200, got {task_list.status_code}: {task_list.text}"
    )
    task_ids = [it.get("id") for it in task_list.json().get("items", [])]
    assert victim_task_id in task_ids, (
        f"Superuser should see task {victim_task_id} in their list. Got ids={task_ids}."
    )
