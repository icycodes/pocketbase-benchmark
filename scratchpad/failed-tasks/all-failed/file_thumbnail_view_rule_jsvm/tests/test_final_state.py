import io
import os
import struct
import zlib
import time

import pytest
import requests

PROJECT_DIR = "/home/user/myproject"
PB_URL = os.environ.get("PB_URL", "http://127.0.0.1:8090")
PB_ADMIN_EMAIL = os.environ.get("PB_ADMIN_EMAIL", "admin@example.com")
PB_ADMIN_PASSWORD = os.environ.get("PB_ADMIN_PASSWORD", "Admin12345!")

OWNER_EMAIL = "owner_thumb@example.com"
OWNER_PASSWORD = "OwnerPass123!"
OTHER_EMAIL = "other_thumb@example.com"
OTHER_PASSWORD = "OtherPass123!"


def _make_png_bytes() -> bytes:
    """Generate a minimal valid 16x16 RGBA PNG in memory."""
    width, height = 16, 16
    # Raw image: each row prefixed with filter byte 0, then RGBA pixels (red, fully opaque).
    raw = b""
    for _ in range(height):
        raw += b"\x00" + (b"\xff\x00\x00\xff" * width)
    compressed = zlib.compress(raw, 9)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        signature
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", compressed)
        + chunk(b"IEND", b"")
    )


def _wait_for_server(timeout_sec: float = 60.0):
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            r = requests.get(f"{PB_URL}/api/health", timeout=2)
            if r.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError(f"PocketBase server at {PB_URL} did not become healthy.")


def _superuser_token() -> str:
    r = requests.post(
        f"{PB_URL}/api/collections/_superusers/auth-with-password",
        json={"identity": PB_ADMIN_EMAIL, "password": PB_ADMIN_PASSWORD},
        timeout=15,
    )
    assert r.status_code == 200, (
        f"Failed to authenticate as superuser: {r.status_code} {r.text}"
    )
    return r.json()["token"]


def _ensure_user(superuser_token: str, email: str, password: str) -> str:
    # Try to fetch by email via list filter
    headers = {"Authorization": superuser_token}
    list_resp = requests.get(
        f"{PB_URL}/api/collections/users/records",
        params={"filter": f"email='{email}'"},
        headers=headers,
        timeout=15,
    )
    assert list_resp.status_code == 200, (
        f"Failed to list users for {email}: {list_resp.status_code} {list_resp.text}"
    )
    items = list_resp.json().get("items") or []
    if items:
        return items[0]["id"]

    create_resp = requests.post(
        f"{PB_URL}/api/collections/users/records",
        json={
            "email": email,
            "password": password,
            "passwordConfirm": password,
            "emailVisibility": True,
            "verified": True,
        },
        headers=headers,
        timeout=15,
    )
    assert create_resp.status_code in (200, 201), (
        f"Failed to create user {email}: {create_resp.status_code} {create_resp.text}"
    )
    return create_resp.json()["id"]


def _user_auth(email: str, password: str) -> str:
    r = requests.post(
        f"{PB_URL}/api/collections/users/auth-with-password",
        json={"identity": email, "password": password},
        timeout=15,
    )
    assert r.status_code == 200, (
        f"User {email} auth failed: {r.status_code} {r.text}"
    )
    return r.json()["token"]


def _file_token(user_token: str) -> str:
    r = requests.post(
        f"{PB_URL}/api/files/token",
        headers={"Authorization": user_token},
        timeout=15,
    )
    assert r.status_code == 200, (
        f"Failed to mint file token: {r.status_code} {r.text}"
    )
    return r.json()["token"]


def _create_photo(user_token: str, owner_id: str, is_public: bool) -> tuple[str, str]:
    files = {"image": ("test.png", _make_png_bytes(), "image/png")}
    data = {
        "owner": owner_id,
        "is_public": "true" if is_public else "false",
    }
    r = requests.post(
        f"{PB_URL}/api/collections/photos/records",
        headers={"Authorization": user_token},
        data=data,
        files=files,
        timeout=30,
    )
    assert r.status_code in (200, 201), (
        f"Failed to create photo (public={is_public}): {r.status_code} {r.text}"
    )
    body = r.json()
    return body["id"], body["image"]


@pytest.fixture(scope="session")
def context():
    _wait_for_server()
    su = _superuser_token()
    owner_id = _ensure_user(su, OWNER_EMAIL, OWNER_PASSWORD)
    other_id = _ensure_user(su, OTHER_EMAIL, OTHER_PASSWORD)

    owner_token = _user_auth(OWNER_EMAIL, OWNER_PASSWORD)
    other_token = _user_auth(OTHER_EMAIL, OTHER_PASSWORD)

    private_id, private_file = _create_photo(owner_token, owner_id, is_public=False)
    public_id, public_file = _create_photo(owner_token, owner_id, is_public=True)

    owner_file_token = _file_token(owner_token)
    other_file_token = _file_token(other_token)

    return {
        "superuser_token": su,
        "owner_id": owner_id,
        "other_id": other_id,
        "owner_token": owner_token,
        "other_token": other_token,
        "owner_file_token": owner_file_token,
        "other_file_token": other_file_token,
        "private_id": private_id,
        "private_file": private_file,
        "public_id": public_id,
        "public_file": public_file,
    }


def _file_url(record_id: str, filename: str) -> str:
    return f"{PB_URL}/api/files/photos/{record_id}/{filename}"


# -------- 1. Collection schema sanity --------

def test_photos_collection_schema(context):
    r = requests.get(
        f"{PB_URL}/api/collections/photos",
        headers={"Authorization": context["superuser_token"]},
        timeout=15,
    )
    assert r.status_code == 200, f"GET photos collection failed: {r.text}"
    coll = r.json()

    assert coll.get("type") == "base", (
        f"photos must be a base collection, got: {coll.get('type')!r}"
    )

    fields = {f["name"]: f for f in coll.get("fields", []) if isinstance(f, dict)}

    assert fields.get("owner", {}).get("type") == "relation", (
        f"photos.owner must be a relation field, got: {fields.get('owner')!r}"
    )

    image_field = fields.get("image", {})
    assert image_field.get("type") == "file", (
        f"photos.image must be a file field, got: {image_field!r}"
    )
    assert set(image_field.get("thumbs") or []) == {"100x100", "400x300t"}, (
        f"photos.image.thumbs must be ['100x100', '400x300t'], got: {image_field.get('thumbs')!r}"
    )

    assert fields.get("is_public", {}).get("type") == "bool", (
        f"photos.is_public must be a bool field, got: {fields.get('is_public')!r}"
    )

    expected_rule = "owner = @request.auth.id || is_public = true"
    actual_rule = coll.get("viewRule") or ""
    assert actual_rule.replace(" ", "") == expected_rule.replace(" ", ""), (
        f"photos.viewRule must equal {expected_rule!r}, got: {actual_rule!r}"
    )


# -------- 2. Owner private photo, predeclared thumb --------

def test_private_predeclared_thumb_owner_can_view(context):
    url = _file_url(context["private_id"], context["private_file"])
    r = requests.get(url, params={"thumb": "100x100", "token": context["owner_file_token"]}, timeout=15)
    assert r.status_code == 200, (
        f"Owner should see private thumb 100x100: {r.status_code} {r.text[:200]}"
    )
    ct = r.headers.get("Content-Type", "")
    assert ct.startswith("image/"), f"Expected image/* Content-Type, got: {ct!r}"


def test_private_predeclared_thumb_other_user_forbidden(context):
    url = _file_url(context["private_id"], context["private_file"])
    r = requests.get(url, params={"thumb": "100x100", "token": context["other_file_token"]}, timeout=15)
    assert r.status_code == 403, (
        f"Other user should be forbidden from private thumb 100x100: {r.status_code} {r.text[:200]}"
    )


def test_private_predeclared_thumb_anonymous_forbidden(context):
    url = _file_url(context["private_id"], context["private_file"])
    r = requests.get(url, params={"thumb": "100x100"}, timeout=15)
    assert r.status_code == 403, (
        f"Anonymous user should be forbidden from private thumb 100x100: {r.status_code} {r.text[:200]}"
    )


# -------- 3. Public photo, predeclared thumb --------

def test_public_predeclared_thumb_anonymous_ok(context):
    url = _file_url(context["public_id"], context["public_file"])
    r = requests.get(url, params={"thumb": "400x300t"}, timeout=15)
    assert r.status_code == 200, (
        f"Anonymous should see public thumb 400x300t: {r.status_code} {r.text[:200]}"
    )
    ct = r.headers.get("Content-Type", "")
    assert ct.startswith("image/"), f"Expected image/* Content-Type, got: {ct!r}"


def test_public_predeclared_thumb_other_user_ok(context):
    url = _file_url(context["public_id"], context["public_file"])
    r = requests.get(url, params={"thumb": "400x300t", "token": context["other_file_token"]}, timeout=15)
    assert r.status_code == 200, (
        f"Other user should see public thumb 400x300t: {r.status_code} {r.text[:200]}"
    )
    ct = r.headers.get("Content-Type", "")
    assert ct.startswith("image/"), f"Expected image/* Content-Type, got: {ct!r}"


# -------- 4. Unsupported thumb blocked by JSVM --------

def test_unsupported_thumb_public_record_returns_400(context):
    url = _file_url(context["public_id"], context["public_file"])
    r = requests.get(url, params={"thumb": "200x200"}, timeout=15)
    assert r.status_code == 400, (
        f"Unsupported thumb on public record must return 400: {r.status_code} {r.text[:200]}"
    )
    body = r.json()
    assert body.get("message") == "unsupported thumb", (
        f"Expected response message 'unsupported thumb', got: {body!r}"
    )


def test_unsupported_thumb_private_record_with_owner_token_returns_400(context):
    url = _file_url(context["private_id"], context["private_file"])
    r = requests.get(url, params={"thumb": "200x200", "token": context["owner_file_token"]}, timeout=15)
    assert r.status_code == 400, (
        f"Unsupported thumb on private record (owner token) must return 400: "
        f"{r.status_code} {r.text[:200]}"
    )
    body = r.json()
    assert body.get("message") == "unsupported thumb", (
        f"Expected response message 'unsupported thumb', got: {body!r}"
    )


# -------- 5. Original (no-thumb) download honors ViewRule --------

def test_original_download_owner_ok(context):
    url = _file_url(context["private_id"], context["private_file"])
    r = requests.get(url, params={"token": context["owner_file_token"]}, timeout=15)
    assert r.status_code == 200, (
        f"Owner should download original private file: {r.status_code} {r.text[:200]}"
    )
    ct = r.headers.get("Content-Type", "")
    assert ct.startswith("image/"), f"Expected image/* Content-Type, got: {ct!r}"


def test_original_download_anonymous_forbidden_on_private(context):
    url = _file_url(context["private_id"], context["private_file"])
    r = requests.get(url, timeout=15)
    assert r.status_code == 403, (
        f"Anonymous should be forbidden from original private file: "
        f"{r.status_code} {r.text[:200]}"
    )


def test_original_download_anonymous_ok_on_public(context):
    url = _file_url(context["public_id"], context["public_file"])
    r = requests.get(url, timeout=15)
    assert r.status_code == 200, (
        f"Anonymous should download original public file: {r.status_code} {r.text[:200]}"
    )
    ct = r.headers.get("Content-Type", "")
    assert ct.startswith("image/"), f"Expected image/* Content-Type, got: {ct!r}"
