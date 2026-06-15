import json
import os
import signal
import subprocess
import time
import urllib.error
import urllib.request

import pytest


PROJECT_DIR = "/home/user/myproject"
PB_URL = "http://127.0.0.1:8090"
SCRIPT_NAME = "subscribe.js"


# ---------------------------- helpers ----------------------------

def _http_post_json(url: str, payload: dict, headers: dict | None = None, timeout: float = 5.0):
    body = json.dumps(payload).encode("utf-8")
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=body, headers=h, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")


def _http_delete(url: str, headers: dict | None = None, timeout: float = 5.0):
    req = urllib.request.Request(url, headers=headers or {}, method="DELETE")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")


def _http_get(url: str, headers: dict | None = None, timeout: float = 5.0):
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")


def _superuser_token() -> str:
    email = os.environ["PB_ADMIN_EMAIL"]
    password = os.environ["PB_ADMIN_PASSWORD"]
    status, body = _http_post_json(
        f"{PB_URL}/api/collections/_superusers/auth-with-password",
        {"identity": email, "password": password},
    )
    assert status == 200, f"Superuser auth failed: status={status} body={body}"
    return json.loads(body)["token"]


def _clean_messages(token: str) -> None:
    # Delete any messages with chat in {A, B} to ensure a clean slate.
    for chat_id in ("A", "B"):
        status, body = _http_get(
            f"{PB_URL}/api/collections/messages/records?perPage=200&filter=" +
            urllib.parse.quote(f'chat="{chat_id}"'),
            headers={"Authorization": token},
        )
        if status != 200:
            continue
        items = json.loads(body).get("items", [])
        for it in items:
            _http_delete(
                f"{PB_URL}/api/collections/messages/records/{it['id']}",
                headers={"Authorization": token},
            )


def _read_available_lines(proc: subprocess.Popen, deadline: float) -> list[str]:
    """Read all already-emitted stdout lines until deadline or EOF."""
    lines: list[str] = []
    assert proc.stdout is not None
    # We rely on the subprocess running with line-buffered stdout (-u not relevant for node;
    # writers should use process.stdout.write(... + "\n") which flushes per line).
    import select
    while time.time() < deadline:
        rlist, _, _ = select.select([proc.stdout], [], [], 0.2)
        if not rlist:
            continue
        line = proc.stdout.readline()
        if line == "":  # EOF
            break
        lines.append(line.rstrip("\n"))
    return lines


import urllib.parse  # noqa: E402  (kept here intentionally; used in _clean_messages)


# ---------------------------- tests ----------------------------

def test_subscribe_script_exists():
    path = os.path.join(PROJECT_DIR, SCRIPT_NAME)
    assert os.path.isfile(path), f"Expected agent script at {path}"


def test_node_modules_installed():
    pkg_dir = os.path.join(PROJECT_DIR, "node_modules", "pocketbase")
    assert os.path.isdir(pkg_dir), (
        f"Expected 'pocketbase' npm package installed at {pkg_dir}. The agent must run npm install."
    )


def test_filtered_subscription_behavior():
    """Launch the agent's script with --chat A, create A/B/A records, assert filter behavior."""
    token = _superuser_token()
    _clean_messages(token)

    env = os.environ.copy()
    # Ensure node-side scripts flush stdout per line.
    env.setdefault("NODE_NO_WARNINGS", "1")

    proc = subprocess.Popen(
        ["node", SCRIPT_NAME, "--chat", "A"],
        cwd=PROJECT_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,  # line-buffered on our (parent) side
        env=env,
    )

    try:
        # Allow the SSE subscription to be established.
        time.sleep(3.0)

        # Confirm the process is still running.
        if proc.poll() is not None:
            stderr_out = (proc.stderr.read() if proc.stderr else "") or ""
            pytest.fail(
                f"Subscriber script exited prematurely with code {proc.returncode}. "
                f"stderr:\n{stderr_out}"
            )

        headers = {"Authorization": token}
        # Create three records: A, B, A.
        created_ids = []
        for payload in (
            {"chat": "A", "body": "hello-A1"},
            {"chat": "B", "body": "hello-B1"},
            {"chat": "A", "body": "hello-A2"},
        ):
            status, body = _http_post_json(
                f"{PB_URL}/api/collections/messages/records",
                payload,
                headers=headers,
            )
            assert status in (200, 201), f"Failed to create record {payload}: status={status} body={body}"
            created_ids.append(json.loads(body)["id"])

        # Wait up to 5 seconds for events, then collect stdout lines.
        deadline = time.time() + 5.0
        lines = _read_available_lines(proc, deadline)

        # Filter out any blank lines.
        non_empty = [ln for ln in lines if ln.strip()]

        # All lines must be valid JSON conforming to schema.
        parsed = []
        for ln in non_empty:
            try:
                obj = json.loads(ln)
            except json.JSONDecodeError as e:
                pytest.fail(f"Non-JSON stdout line emitted by script: {ln!r} ({e})")
            assert isinstance(obj, dict), f"Stdout line is not a JSON object: {ln!r}"
            assert "action" in obj, f"Missing 'action' key in JSON line: {ln!r}"
            assert "record" in obj, f"Missing 'record' key in JSON line: {ln!r}"
            assert isinstance(obj["record"], dict), f"'record' is not a JSON object: {ln!r}"
            parsed.append(obj)

        # No events for chat=B may appear.
        b_events = [p for p in parsed if p["record"].get("chat") == "B"]
        assert not b_events, (
            f"Subscriber leaked events for chat=B: {b_events}. The filter must block them."
        )

        # Exactly 2 create events for chat=A.
        create_a = [
            p for p in parsed
            if p["action"] == "create" and p["record"].get("chat") == "A"
        ]
        assert len(create_a) == 2, (
            f"Expected exactly 2 create events with chat=A, got {len(create_a)}. "
            f"All parsed events: {parsed}"
        )

        bodies = sorted(p["record"].get("body") for p in create_a)
        assert bodies == ["hello-A1", "hello-A2"], (
            f"Expected the two delivered records to have bodies 'hello-A1' and 'hello-A2', "
            f"got {bodies}"
        )

        ids = [p["record"].get("id") for p in create_a]
        for rid in ids:
            assert isinstance(rid, str) and rid, f"record.id must be a non-empty string, got {rid!r}"

    finally:
        # Cleanup: send SIGTERM and verify clean exit (acceptance criterion).
        if proc.poll() is None:
            proc.send_signal(signal.SIGTERM)
            try:
                rc = proc.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=2.0)
                pytest.fail("Subscriber did not exit within 3 seconds after SIGTERM.")
            else:
                assert rc == 0, f"Subscriber should exit with code 0 on SIGTERM, got {rc}."

        # Drain any remaining output and clean up DB.
        try:
            _clean_messages(token)
        except Exception:
            pass
