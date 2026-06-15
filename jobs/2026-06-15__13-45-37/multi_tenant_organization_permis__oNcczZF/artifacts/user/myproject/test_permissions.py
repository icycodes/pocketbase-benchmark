import urllib.request
import urllib.error
import json
import sys

BASE_URL = "http://127.0.0.1:8090"

def make_request(method, path, body=None, token=None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req) as response:
            status = response.status
            res_body = response.read().decode("utf-8")
            try:
                return status, json.loads(res_body)
            except Exception:
                return status, res_body
    except urllib.error.HTTPError as e:
        status = e.code
        res_body = e.read().decode("utf-8")
        try:
            return status, json.loads(res_body)
        except Exception:
            return status, res_body
    except Exception as e:
        return 500, str(e)

def setup_user(email, password="password123"):
    # Attempt to create user
    print(f"Creating user {email}...")
    status, res = make_request("POST", "/api/collections/users/records", {
        "email": email,
        "password": password,
        "passwordConfirm": password
    })
    if status not in (200, 201):
        print(f"  User creation returned status {status}: {res.get('message', res) if isinstance(res, dict) else res}")
    
    # Login to get token and ID
    print(f"Logging in {email}...")
    status, res = make_request("POST", "/api/collections/users/auth-with-password", {
        "identity": email,
        "password": password
    })
    if status != 200:
        raise Exception(f"Failed to login user {email}: {res}")
    return res["record"]["id"], res["token"]

def main():
    print("=== MULTI-TENANT PERMISSION TEST SUITE ===")
    
    # 1. Setup Users
    users = {}
    for role in ["owner", "editor", "viewer", "outsider"]:
        uid, token = setup_user(f"{role}@example.com")
        users[role] = {"id": uid, "token": token}
    
    # 2. Create Organization Org A using owner
    print("\n--- Organization Setup ---")
    print("Creating Organization Org A...")
    status, org = make_request("POST", "/api/collections/organizations/records", {
        "name": "Org A"
    }, token=users["owner"]["token"])
    if status not in (200, 201):
        print(f"Failed to create organization: {org}")
        sys.exit(1)
    org_id = org["id"]
    print(f"Created Org A with ID: {org_id}")

    # 3. Create Membership Records
    print("Adding members to Org A...")
    for role in ["owner", "editor", "viewer"]:
        status, mem = make_request("POST", "/api/collections/organization_members/records", {
            "user": users[role]["id"],
            "organization": org_id,
            "role": role
        }, token=users["owner"]["token"])
        if status not in (200, 201):
            print(f"Failed to add {role} membership: {mem}")
            sys.exit(1)
        print(f"  Added {role} with role '{role}'")

    # 4. Run Permission Tests
    print("\n--- Document Creation Tests ---")
    
    # Viewer tries to create document in Org A -> Should fail
    print("Testing: Viewer tries to create a document in Org A (Should FAIL)...")
    status, res = make_request("POST", "/api/collections/documents/records", {
        "title": "Viewer Doc",
        "content": "Secret content",
        "organization": org_id
    }, token=users["viewer"]["token"])
    print(f"  Result: Status {status} (Expected: 400 or 403 or 404)")
    assert status in (400, 403, 404), f"Expected failure, got {status}"
    
    # Outsider tries to create document in Org A -> Should fail
    print("Testing: Outsider tries to create a document in Org A (Should FAIL)...")
    status, res = make_request("POST", "/api/collections/documents/records", {
        "title": "Outsider Doc",
        "content": "Secret content",
        "organization": org_id
    }, token=users["outsider"]["token"])
    print(f"  Result: Status {status} (Expected: 400 or 403 or 404)")
    assert status in (400, 403, 404), f"Expected failure, got {status}"

    # Editor tries to create document in Org A -> Should succeed
    print("Testing: Editor tries to create a document in Org A (Should SUCCEED)...")
    status, doc_editor = make_request("POST", "/api/collections/documents/records", {
        "title": "Editor Doc",
        "content": "Content by editor",
        "organization": org_id
    }, token=users["editor"]["token"])
    print(f"  Result: Status {status} (Expected: 200 or 201)")
    assert status in (200, 201), f"Expected success, got {status}"
    doc_id = doc_editor["id"]

    # Owner tries to create document in Org A -> Should succeed
    print("Testing: Owner tries to create a document in Org A (Should SUCCEED)...")
    status, doc_owner = make_request("POST", "/api/collections/documents/records", {
        "title": "Owner Doc",
        "content": "Content by owner",
        "organization": org_id
    }, token=users["owner"]["token"])
    print(f"  Result: Status {status} (Expected: 200 or 201)")
    assert status in (200, 201), f"Expected success, got {status}"

    print("\n--- Document List/View Tests ---")
    
    # Outsider tries to list documents -> Should not see the documents (empty list)
    print("Testing: Outsider lists documents (Should see empty list)...")
    status, list_res = make_request("GET", "/api/collections/documents/records", token=users["outsider"]["token"])
    print(f"  Result: Status {status}, Items found: {len(list_res.get('items', []))}")
    assert status == 200 and len(list_res.get('items', [])) == 0, f"Expected empty list, got {list_res}"

    # Viewer lists documents -> Should see the documents (length 2)
    print("Testing: Viewer lists documents (Should see 2 documents)...")
    status, list_res = make_request("GET", "/api/collections/documents/records", token=users["viewer"]["token"])
    print(f"  Result: Status {status}, Items found: {len(list_res.get('items', []))}")
    assert status == 200 and len(list_res.get('items', [])) == 2, f"Expected 2 documents, got {list_res}"

    # Outsider tries to view Editor Doc directly -> Should fail
    print("Testing: Outsider views Editor Doc directly (Should FAIL)...")
    status, res = make_request("GET", f"/api/collections/documents/records/{doc_id}", token=users["outsider"]["token"])
    print(f"  Result: Status {status} (Expected: 404 or 403)")
    assert status in (403, 404), f"Expected failure, got {status}"

    # Viewer views Editor Doc directly -> Should succeed
    print("Testing: Viewer views Editor Doc directly (Should SUCCEED)...")
    status, res = make_request("GET", f"/api/collections/documents/records/{doc_id}", token=users["viewer"]["token"])
    print(f"  Result: Status {status} (Expected: 200)")
    assert status == 200, f"Expected success, got {status}"

    print("\n--- Document Update Tests ---")
    
    # Outsider tries to update Editor Doc -> Should fail
    print("Testing: Outsider updates Editor Doc (Should FAIL)...")
    status, res = make_request("PATCH", f"/api/collections/documents/records/{doc_id}", {
        "title": "Hacked title"
    }, token=users["outsider"]["token"])
    print(f"  Result: Status {status} (Expected: 400 or 403 or 404)")
    assert status in (400, 403, 404), f"Expected failure, got {status}"

    # Viewer tries to update Editor Doc -> Should fail
    print("Testing: Viewer updates Editor Doc (Should FAIL)...")
    status, res = make_request("PATCH", f"/api/collections/documents/records/{doc_id}", {
        "title": "Viewer update"
    }, token=users["viewer"]["token"])
    print(f"  Result: Status {status} (Expected: 400 or 403 or 404)")
    assert status in (400, 403, 404), f"Expected failure, got {status}"

    # Editor updates Editor Doc -> Should succeed
    print("Testing: Editor updates Editor Doc (Should SUCCEED)...")
    status, res = make_request("PATCH", f"/api/collections/documents/records/{doc_id}", {
        "title": "Updated title by editor"
    }, token=users["editor"]["token"])
    print(f"  Result: Status {status} (Expected: 200)")
    assert status == 200, f"Expected success, got {status}"

    print("\n--- Document Delete Tests ---")
    
    # Outsider tries to delete Editor Doc -> Should fail
    print("Testing: Outsider deletes Editor Doc (Should FAIL)...")
    status, res = make_request("DELETE", f"/api/collections/documents/records/{doc_id}", token=users["outsider"]["token"])
    print(f"  Result: Status {status} (Expected: 400 or 403 or 404)")
    assert status in (400, 403, 404), f"Expected failure, got {status}"

    # Editor tries to delete Editor Doc -> Should fail
    print("Testing: Editor deletes Editor Doc (Should FAIL)...")
    status, res = make_request("DELETE", f"/api/collections/documents/records/{doc_id}", token=users["editor"]["token"])
    print(f"  Result: Status {status} (Expected: 400 or 403 or 404)")
    assert status in (400, 403, 404), f"Expected failure, got {status}"

    # Owner deletes Editor Doc -> Should succeed
    print("Testing: Owner deletes Editor Doc (Should SUCCEED)...")
    status, res = make_request("DELETE", f"/api/collections/documents/records/{doc_id}", token=users["owner"]["token"])
    print(f"  Result: Status {status} (Expected: 204)")
    assert status in (200, 204), f"Expected success, got {status}"

    print("\n=== ALL TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    main()
