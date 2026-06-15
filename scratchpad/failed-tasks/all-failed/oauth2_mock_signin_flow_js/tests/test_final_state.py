import json
import os
import subprocess

import pytest
import requests

PROJECT_DIR = "/home/user/myproject"
PB_URL = os.environ.get("PB_URL", "http://127.0.0.1:8090")
MOCK_OAUTH_URL = os.environ.get("MOCK_OAUTH_URL", "http://127.0.0.1:9000")
PB_SUPERUSER_EMAIL = os.environ.get("PB_SUPERUSER_EMAIL", "")
PB_SUPERUSER_PASSWORD = os.environ.get("PB_SUPERUSER_PASSWORD", "")

STDOUT_PATH = "/tmp/app_stdout.json"


def _superuser_token() -> str:
    resp = requests.post(
        f"{PB_URL}/api/collections/_superusers/auth-with-password",
        json={"identity": PB_SUPERUSER_EMAIL, "password": PB_SUPERUSER_PASSWORD},
        timeout=10,
    )
    assert resp.status_code == 200, (
        f"Failed to authenticate superuser: {resp.status_code} {resp.text}"
    )
    token = resp.json().get("token")
    assert token, "Superuser auth response did not contain a token."
    return token


@pytest.fixture(scope="module")
def run_cli_and_capture_stdout():
    if os.path.isfile(STDOUT_PATH):
        os.remove(STDOUT_PATH)
    result = subprocess.run(
        ["node", "app.js"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, (
        f"`node app.js` exited with non-zero code {result.returncode}. "
        f"stderr:\n{result.stderr}\nstdout:\n{result.stdout}"
    )
    with open(STDOUT_PATH, "w", encoding="utf-8") as f:
        f.write(result.stdout)
    return result


@pytest.fixture(scope="module")
def stdout_user_record(run_cli_and_capture_stdout):
    stdout = run_cli_and_capture_stdout.stdout.strip()
    assert stdout, "`node app.js` produced empty stdout."
    try:
        record = json.loads(stdout)
    except json.JSONDecodeError as e:
        raise AssertionError(
            f"stdout is not valid JSON: {e}. Raw stdout:\n{stdout}"
        )
    assert isinstance(record, dict), (
        f"stdout JSON must be a single object, got: {type(record).__name__}"
    )
    return record


def test_stdout_record_has_required_fields(stdout_user_record):
    record = stdout_user_record
    user_id = record.get("id")
    assert isinstance(user_id, str) and user_id, (
        f"stdout JSON must contain a non-empty string `id`, got: {user_id!r}"
    )
    assert record.get("email") == "oauth-user@example.com", (
        f"stdout JSON `email` should be 'oauth-user@example.com', got: {record.get('email')!r}"
    )
    assert record.get("verified") is True, (
        f"stdout JSON `verified` should be True, got: {record.get('verified')!r}"
    )


def test_user_record_persisted_via_rest_api(stdout_user_record):
    user_id = stdout_user_record["id"]
    token = _superuser_token()
    resp = requests.get(
        f"{PB_URL}/api/collections/users/records/{user_id}",
        headers={"Authorization": token},
        timeout=10,
    )
    assert resp.status_code == 200, (
        f"Expected to fetch users/{user_id}, got {resp.status_code}: {resp.text}"
    )
    user = resp.json()
    assert user.get("email") == "oauth-user@example.com", (
        f"Persisted user email mismatch: {user.get('email')!r}"
    )
    assert user.get("verified") is True, (
        f"Persisted user `verified` should be True, got {user.get('verified')!r}"
    )


def test_external_auth_link_to_mockoauth_provider(stdout_user_record):
    user_id = stdout_user_record["id"]
    token = _superuser_token()

    # Discover the provider name configured on the users collection that
    # has displayName == 'mockoauth'. In PocketBase v0.31 custom OAuth2
    # providers are exposed via the generic 'oidc'/'oidc2'/'oidc3' slots.
    coll_resp = requests.get(
        f"{PB_URL}/api/collections/users",
        headers={"Authorization": token},
        timeout=10,
    )
    assert coll_resp.status_code == 200, (
        f"Failed to fetch users collection: {coll_resp.status_code} {coll_resp.text}"
    )
    providers = (coll_resp.json().get("oauth2") or {}).get("providers") or []
    matching = [p for p in providers if p.get("displayName") == "mockoauth"]
    assert matching, (
        f"users collection has no provider with displayName 'mockoauth'. "
        f"Providers: {providers}"
    )
    expected_provider_name = matching[0].get("name")
    assert expected_provider_name, (
        f"Configured 'mockoauth' provider is missing a `name`: {matching[0]}"
    )

    ext_resp = requests.get(
        f"{PB_URL}/api/collections/_externalAuths/records",
        headers={"Authorization": token},
        params={"filter": f"recordRef='{user_id}'", "perPage": 50},
        timeout=10,
    )
    assert ext_resp.status_code == 200, (
        f"Failed to list _externalAuths records: {ext_resp.status_code} {ext_resp.text}"
    )
    items = ext_resp.json().get("items") or []
    assert items, (
        f"Expected at least one _externalAuths record linked to user {user_id}, got none."
    )

    linked = [it for it in items if it.get("provider") == expected_provider_name]
    assert linked, (
        f"Expected an _externalAuths record with provider == {expected_provider_name!r} "
        f"linked to user {user_id}. Got: {items}"
    )
    provider_id = linked[0].get("providerId")
    assert isinstance(provider_id, str) and provider_id, (
        f"Linked _externalAuths record should have a non-empty providerId, got: {provider_id!r}"
    )


def test_provider_endpoints_point_to_mock_server():
    token = _superuser_token()
    resp = requests.get(
        f"{PB_URL}/api/collections/users",
        headers={"Authorization": token},
        timeout=10,
    )
    assert resp.status_code == 200, (
        f"Failed to fetch users collection: {resp.status_code} {resp.text}"
    )
    oauth2 = resp.json().get("oauth2") or {}
    assert oauth2.get("enabled") is True, (
        "users collection oauth2 should be enabled."
    )
    providers = [p for p in (oauth2.get("providers") or []) if p.get("displayName") == "mockoauth"]
    assert len(providers) == 1, (
        f"Expected exactly one 'mockoauth' provider, got {len(providers)}: {providers}"
    )
    provider = providers[0]
    for key in ("authURL", "tokenURL", "userInfoURL"):
        url = provider.get(key, "")
        assert isinstance(url, str) and url.startswith(MOCK_OAUTH_URL), (
            f"Provider {key} must start with {MOCK_OAUTH_URL}, got {url!r}"
        )
