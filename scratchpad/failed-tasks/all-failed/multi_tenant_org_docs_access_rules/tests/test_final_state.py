"""Final-state behavioural tests for the PocketBase multi-tenant task.

The PocketBase server is started by the ``pocketbase_server`` session fixture
(it is reused if already running on port 8090). The ``seed`` fixture provisions
the canonical org/membership/document graph via superuser-authenticated REST
calls. All assertions are then expressed exclusively through the public
PocketBase HTTP API.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import time
from typing import Any
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest

import pytest

PROJECT_DIR = "/home/user/myproject"
POCKETBASE_BIN = os.path.join(PROJECT_DIR, "pocketbase")
PB_DATA_DIR = os.path.join(PROJECT_DIR, "pb_data")
PB_MIGRATIONS_DIR = os.path.join(PROJECT_DIR, "pb_migrations")
PB_BASE_URL = "http://127.0.0.1:8090"

SUPERUSER_EMAIL = "admin@example.com"
SUPERUSER_PASSWORD = "Adm1n_Password!"

ALICE_EMAIL = "alice@example.com"
ALICE_PASSWORD = "Alice_Password1!"
BOB_EMAIL = "bob@example.com"
BOB_PASSWORD = "Bob_Password1!"
CAROL_EMAIL = "carol@example.com"
CAROL_PASSWORD = "Carol_Password1!"


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _request(
    method: str,
    path: str,
    body: Any = None,
    token: str | None = None,
    query: dict | None = None,
    timeout: float = 10.0,
) -> tuple[int, Any]:
    url = f"{PB_BASE_URL}{path}"
    if query:
        url = f"{url}?{urlparse.urlencode(query)}"
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = token
    req = urlrequest.Request(url, data=data, method=method, headers=headers)
    try:
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else None
    except urlerror.HTTPError as e:
        try:
            payload = json.loads(e.read().decode("utf-8") or "null")
        except Exception:
            payload = None
        return e.code, payload


def _port_open(host: str, port: int) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.5)
    try:
        return sock.connect_ex((host, port)) == 0
    finally:
        sock.close()


def _wait_for_health(timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            status, _ = _request("GET", "/api/health", timeout=2.0)
            if status == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def _auth_with_password(collection: str, identity: str, password: str) -> str:
    status, payload = _request(
        "POST",
        f"/api/collections/{collection}/auth-with-password",
        body={"identity": identity, "password": password},
    )
    assert status == 200 and isinstance(payload, dict) and payload.get("token"), (
        f"Auth as {identity!r} on collection {collection!r} failed: "
        f"status={status} payload={payload!r}"
    )
    return payload["token"]


def _find_record_id(
    superuser_token: str,
    collection: str,
    field: str,
    value: str,
) -> str | None:
    status, payload = _request(
        "GET",
        f"/api/collections/{collection}/records",
        token=superuser_token,
        query={
            "filter": f"{field}={json.dumps(value)}",
            "perPage": "200",
        },
    )
    assert status == 200, (
        f"Lookup on {collection}.{field}={value!r} failed: "
        f"status={status} payload={payload!r}"
    )
    items = (payload or {}).get("items") or []
    return items[0]["id"] if items else None


def _ensure_org(superuser_token: str, name: str) -> str:
    existing = _find_record_id(superuser_token, "organizations", "name", name)
    if existing:
        return existing
    status, payload = _request(
        "POST",
        "/api/collections/organizations/records",
        body={"name": name},
        token=superuser_token,
    )
    assert status in (200, 201) and isinstance(payload, dict), (
        f"Could not create organization {name!r}: status={status} payload={payload!r}"
    )
    return payload["id"]


def _ensure_user(superuser_token: str, email: str, password: str) -> str:
    existing = _find_record_id(superuser_token, "users", "email", email)
    if existing:
        return existing
    body = {
        "email": email,
        "password": password,
        "passwordConfirm": password,
        "emailVisibility": True,
        "verified": True,
        "name": email.split("@")[0],
    }
    status, payload = _request(
        "POST",
        "/api/collections/users/records",
        body=body,
        token=superuser_token,
    )
    assert status in (200, 201) and isinstance(payload, dict), (
        f"Could not create user {email!r}: status={status} payload={payload!r}"
    )
    return payload["id"]


def _ensure_membership(
    superuser_token: str, org_id: str, user_id: str, role: str
) -> str:
    status, payload = _request(
        "GET",
        "/api/collections/memberships/records",
        token=superuser_token,
        query={
            "filter": f'org="{org_id}" && user="{user_id}"',
            "perPage": "200",
        },
    )
    assert status == 200, (
        f"Membership lookup failed: status={status} payload={payload!r}"
    )
    items = (payload or {}).get("items") or []
    if items:
        existing = items[0]
        if existing.get("role") != role:
            up_status, up_payload = _request(
                "PATCH",
                f"/api/collections/memberships/records/{existing['id']}",
                body={"role": role},
                token=superuser_token,
            )
            assert up_status == 200, (
                f"Could not update membership role: status={up_status} "
                f"payload={up_payload!r}"
            )
        return existing["id"]
    status, payload = _request(
        "POST",
        "/api/collections/memberships/records",
        body={"org": org_id, "user": user_id, "role": role},
        token=superuser_token,
    )
    assert status in (200, 201) and isinstance(payload, dict), (
        f"Could not create membership: status={status} payload={payload!r}"
    )
    return payload["id"]


def _ensure_document(
    superuser_token: str, org_id: str, title: str, content: str
) -> str:
    existing_id = _find_record_id(superuser_token, "documents", "title", title)
    if existing_id:
        # Reset content/org to known values so retries are deterministic.
        _request(
            "PATCH",
            f"/api/collections/documents/records/{existing_id}",
            body={"org": org_id, "title": title, "content": content},
            token=superuser_token,
        )
        return existing_id
    status, payload = _request(
        "POST",
        "/api/collections/documents/records",
        body={"org": org_id, "title": title, "content": content},
        token=superuser_token,
    )
    assert status in (200, 201) and isinstance(payload, dict), (
        f"Could not create document {title!r}: status={status} payload={payload!r}"
    )
    return payload["id"]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def pocketbase_server():
    if not _port_open("127.0.0.1", 8090):
        log_path = os.path.join(PROJECT_DIR, "pocketbase-server.log")
        log_file = open(log_path, "ab", buffering=0)
        subprocess.Popen(
            [
                POCKETBASE_BIN,
                "serve",
                "--http=0.0.0.0:8090",
                f"--dir={PB_DATA_DIR}",
                f"--migrationsDir={PB_MIGRATIONS_DIR}",
            ],
            cwd=PROJECT_DIR,
            stdout=log_file,
            stderr=log_file,
            close_fds=True,
        )
    assert _wait_for_health(timeout=60.0), (
        "PocketBase server did not become healthy within 60s on "
        f"{PB_BASE_URL}."
    )
    yield


@pytest.fixture(scope="session")
def superuser_token(pocketbase_server) -> str:
    return _auth_with_password("_superusers", SUPERUSER_EMAIL, SUPERUSER_PASSWORD)


@pytest.fixture(scope="session")
def seed(superuser_token: str) -> dict:
    """Seed (idempotently) the canonical orgs/users/memberships/documents."""
    org_x = _ensure_org(superuser_token, "OrgX")
    org_y = _ensure_org(superuser_token, "OrgY")

    alice = _ensure_user(superuser_token, ALICE_EMAIL, ALICE_PASSWORD)
    bob = _ensure_user(superuser_token, BOB_EMAIL, BOB_PASSWORD)
    carol = _ensure_user(superuser_token, CAROL_EMAIL, CAROL_PASSWORD)

    _ensure_membership(superuser_token, org_x, alice, "viewer")
    _ensure_membership(superuser_token, org_x, bob, "editor")
    _ensure_membership(superuser_token, org_y, carol, "editor")

    doc_x1 = _ensure_document(superuser_token, org_x, "OrgX Doc 1", "hello")
    doc_x2 = _ensure_document(superuser_token, org_x, "OrgX Doc 2", "world")
    doc_y1 = _ensure_document(superuser_token, org_y, "OrgY Doc 1", "private")

    return {
        "org_x": org_x,
        "org_y": org_y,
        "alice_id": alice,
        "bob_id": bob,
        "carol_id": carol,
        "doc_x1": doc_x1,
        "doc_x2": doc_x2,
        "doc_y1": doc_y1,
    }


@pytest.fixture(scope="session")
def alice_token(seed) -> str:
    return _auth_with_password("users", ALICE_EMAIL, ALICE_PASSWORD)


@pytest.fixture(scope="session")
def bob_token(seed) -> str:
    return _auth_with_password("users", BOB_EMAIL, BOB_PASSWORD)


@pytest.fixture(scope="session")
def carol_token(seed) -> str:
    return _auth_with_password("users", CAROL_EMAIL, CAROL_PASSWORD)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_collections_present(superuser_token: str):
    status, payload = _request(
        "GET",
        "/api/collections",
        token=superuser_token,
        query={"perPage": "500"},
    )
    assert status == 200, (
        f"Listing collections failed: status={status} payload={payload!r}"
    )
    names = {c["name"] for c in (payload or {}).get("items", [])}
    for required in ("organizations", "memberships", "documents"):
        assert required in names, (
            f"Required collection {required!r} not found; got: {sorted(names)}"
        )


def test_memberships_role_is_select_viewer_editor(superuser_token: str):
    status, payload = _request(
        "GET",
        "/api/collections/memberships",
        token=superuser_token,
    )
    assert status == 200, (
        f"Inspecting memberships collection failed: status={status} payload={payload!r}"
    )
    fields = (payload or {}).get("fields") or (payload or {}).get("schema") or []
    role_field = next((f for f in fields if f.get("name") == "role"), None)
    assert role_field is not None, (
        f"memberships.role field not found; fields={fields!r}"
    )
    assert role_field.get("type") == "select", (
        f"memberships.role must be a select field, got: {role_field!r}"
    )
    max_select = role_field.get("maxSelect")
    assert max_select in (None, 1), (
        f"memberships.role must be single-select (maxSelect<=1), got {max_select!r}"
    )
    values = set(role_field.get("values") or role_field.get("options") or [])
    assert values == {"viewer", "editor"}, (
        f"memberships.role options must be exactly {{viewer, editor}}, got {values!r}"
    )


def test_alice_lists_only_orgx_documents(seed, alice_token: str):
    status, payload = _request(
        "GET",
        "/api/collections/documents/records",
        token=alice_token,
        query={"perPage": "200"},
    )
    assert status == 200, (
        f"Authenticated list for alice failed: status={status} payload={payload!r}"
    )
    ids = {r["id"] for r in (payload or {}).get("items", [])}
    assert seed["doc_x1"] in ids and seed["doc_x2"] in ids, (
        f"Alice (OrgX viewer) should see both OrgX docs, got ids={ids!r}"
    )
    assert seed["doc_y1"] not in ids, (
        f"Alice (OrgX viewer) MUST NOT see OrgY doc, got ids={ids!r}"
    )


def test_carol_lists_only_orgy_documents(seed, carol_token: str):
    status, payload = _request(
        "GET",
        "/api/collections/documents/records",
        token=carol_token,
        query={"perPage": "200"},
    )
    assert status == 200, (
        f"Authenticated list for carol failed: status={status} payload={payload!r}"
    )
    ids = {r["id"] for r in (payload or {}).get("items", [])}
    assert seed["doc_y1"] in ids, (
        f"Carol (OrgY editor) should see OrgY doc, got ids={ids!r}"
    )
    assert seed["doc_x1"] not in ids and seed["doc_x2"] not in ids, (
        f"Carol (OrgY editor) MUST NOT see any OrgX doc, got ids={ids!r}"
    )


def test_alice_cross_tenant_view_returns_404(seed, alice_token: str):
    status, payload = _request(
        "GET",
        f"/api/collections/documents/records/{seed['doc_y1']}",
        token=alice_token,
    )
    assert status == 404, (
        f"Alice viewing OrgY doc must return 404, got status={status} payload={payload!r}"
    )


def test_alice_in_tenant_view_succeeds(seed, alice_token: str):
    status, payload = _request(
        "GET",
        f"/api/collections/documents/records/{seed['doc_x1']}",
        token=alice_token,
    )
    assert status == 200 and isinstance(payload, dict) and payload.get("id") == seed["doc_x1"], (
        f"Alice viewing OrgX doc must return 200 with the record, got "
        f"status={status} payload={payload!r}"
    )


def test_viewer_cannot_create_document(seed, alice_token: str):
    status, payload = _request(
        "POST",
        "/api/collections/documents/records",
        token=alice_token,
        body={"org": seed["org_x"], "title": "viewer-attempt", "content": "blocked"},
    )
    assert status in (400, 403), (
        f"Alice (viewer) creating in OrgX must fail with 400/403, got "
        f"status={status} payload={payload!r}"
    )


def test_editor_can_create_document(seed, bob_token: str, superuser_token: str):
    title = "bob-new-doc"
    status, payload = _request(
        "POST",
        "/api/collections/documents/records",
        token=bob_token,
        body={"org": seed["org_x"], "title": title, "content": "from bob"},
    )
    assert status in (200, 201) and isinstance(payload, dict), (
        f"Bob (editor of OrgX) creating in OrgX must succeed, got "
        f"status={status} payload={payload!r}"
    )
    assert payload.get("org") == seed["org_x"], (
        f"Created doc.org should be OrgX, got {payload!r}"
    )
    # cleanup so retries stay deterministic
    if payload.get("id"):
        _request(
            "DELETE",
            f"/api/collections/documents/records/{payload['id']}",
            token=superuser_token,
        )


def test_editor_cannot_create_in_other_tenant(seed, bob_token: str):
    status, payload = _request(
        "POST",
        "/api/collections/documents/records",
        token=bob_token,
        body={"org": seed["org_y"], "title": "bob-cross-tenant", "content": "nope"},
    )
    assert status in (400, 403), (
        f"Bob (editor of OrgX) creating in OrgY must fail with 400/403, got "
        f"status={status} payload={payload!r}"
    )


def test_viewer_cannot_update_document(seed, alice_token: str, superuser_token: str):
    original_status, original_payload = _request(
        "GET",
        f"/api/collections/documents/records/{seed['doc_x1']}",
        token=superuser_token,
    )
    assert original_status == 200 and isinstance(original_payload, dict), (
        f"Superuser GET of doc_x1 failed: status={original_status} payload={original_payload!r}"
    )
    original_title = original_payload.get("title")

    status, payload = _request(
        "PATCH",
        f"/api/collections/documents/records/{seed['doc_x1']}",
        token=alice_token,
        body={"title": "hacked-by-viewer"},
    )
    assert status == 404, (
        f"Alice (viewer) PATCH on docX1 must return 404, got "
        f"status={status} payload={payload!r}"
    )

    after_status, after_payload = _request(
        "GET",
        f"/api/collections/documents/records/{seed['doc_x1']}",
        token=superuser_token,
    )
    assert after_status == 200 and isinstance(after_payload, dict), (
        f"Superuser re-fetch failed: status={after_status} payload={after_payload!r}"
    )
    assert after_payload.get("title") == original_title, (
        f"docX1.title must be unchanged after viewer PATCH attempt: "
        f"was {original_title!r}, now {after_payload.get('title')!r}"
    )


def test_editor_can_update_document(seed, bob_token: str, superuser_token: str):
    new_title = "OrgX Doc 1 - edited by Bob"
    status, payload = _request(
        "PATCH",
        f"/api/collections/documents/records/{seed['doc_x1']}",
        token=bob_token,
        body={"title": new_title},
    )
    assert status == 200 and isinstance(payload, dict), (
        f"Bob (editor of OrgX) PATCH must return 200, got "
        f"status={status} payload={payload!r}"
    )
    assert payload.get("title") == new_title, (
        f"Updated title must be reflected in response, got {payload!r}"
    )
    # Restore original title so this test is idempotent.
    _request(
        "PATCH",
        f"/api/collections/documents/records/{seed['doc_x1']}",
        token=superuser_token,
        body={"title": "OrgX Doc 1"},
    )


def test_cross_tenant_editor_cannot_update(seed, carol_token: str):
    status, payload = _request(
        "PATCH",
        f"/api/collections/documents/records/{seed['doc_x1']}",
        token=carol_token,
        body={"title": "cross-tenant-hack"},
    )
    assert status == 404, (
        f"Carol (editor of OrgY) PATCH on docX1 must return 404, got "
        f"status={status} payload={payload!r}"
    )


def test_org_field_cannot_be_changed(seed, bob_token: str, superuser_token: str):
    status, payload = _request(
        "PATCH",
        f"/api/collections/documents/records/{seed['doc_x1']}",
        token=bob_token,
        body={"org": seed["org_y"]},
    )
    assert status in (400, 403), (
        f"Bob (editor) attempting to move docX1 to OrgY must fail with 400/403, got "
        f"status={status} payload={payload!r}"
    )
    confirm_status, confirm_payload = _request(
        "GET",
        f"/api/collections/documents/records/{seed['doc_x1']}",
        token=superuser_token,
    )
    assert confirm_status == 200 and isinstance(confirm_payload, dict), (
        f"Superuser re-fetch failed: status={confirm_status} payload={confirm_payload!r}"
    )
    assert confirm_payload.get("org") == seed["org_x"], (
        f"docX1.org must remain OrgX after blocked attempt, got {confirm_payload!r}"
    )


def test_guest_cannot_list_documents(seed, superuser_token: str):
    status, payload = _request(
        "GET",
        "/api/collections/documents/records",
        query={"perPage": "200"},
    )
    if status == 200:
        items = (payload or {}).get("items") or []
        assert items == [], (
            f"Guest list MUST NOT leak documents; got items={items!r}"
        )
    else:
        assert status in (401, 403), (
            f"Guest list must be denied or empty, got status={status} payload={payload!r}"
        )


def test_guest_cannot_view_document(seed):
    status, payload = _request(
        "GET",
        f"/api/collections/documents/records/{seed['doc_x1']}",
    )
    assert status in (401, 403, 404), (
        f"Guest viewing doc must be denied, got status={status} payload={payload!r}"
    )


def test_guest_cannot_create_or_update(seed, superuser_token: str):
    create_status, create_payload = _request(
        "POST",
        "/api/collections/documents/records",
        body={"org": seed["org_x"], "title": "guest-create", "content": "x"},
    )
    assert create_status in (400, 401, 403), (
        f"Guest POST must be denied, got status={create_status} payload={create_payload!r}"
    )
    # No record was created with that title.
    leaked = _find_record_id(superuser_token, "documents", "title", "guest-create")
    assert leaked is None, "Guest POST must not create a document, but one exists."

    patch_status, patch_payload = _request(
        "PATCH",
        f"/api/collections/documents/records/{seed['doc_x1']}",
        body={"title": "guest-hacked"},
    )
    assert patch_status in (401, 403, 404), (
        f"Guest PATCH must be denied, got status={patch_status} payload={patch_payload!r}"
    )
    confirm_status, confirm_payload = _request(
        "GET",
        f"/api/collections/documents/records/{seed['doc_x1']}",
        token=superuser_token,
    )
    assert confirm_status == 200 and isinstance(confirm_payload, dict), (
        f"Superuser re-fetch failed: status={confirm_status} payload={confirm_payload!r}"
    )
    assert confirm_payload.get("title") != "guest-hacked", (
        f"docX1.title must not be changed by guest, got {confirm_payload!r}"
    )
