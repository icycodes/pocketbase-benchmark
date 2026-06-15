import urllib.request
import json
import sys

BASE_URL = "http://localhost:8090/api"

def make_request(url, method, data=None, token=None):
    req = urllib.request.Request(url, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    
    body = json.dumps(data).encode("utf-8") if data else None
    try:
        with urllib.request.urlopen(req, data=body) as res:
            return res.status, json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            err_body = json.loads(e.read().decode("utf-8"))
        except Exception:
            err_body = e.reason
        return e.code, err_body

def run_tests():
    print("--- 1. Creating user1 ---")
    status, res = make_request(
        f"{BASE_URL}/collections/users/records",
        "POST",
        {
            "email": "user1@example.com",
            "password": "password123456",
            "passwordConfirm": "password123456"
        }
    )
    print(f"Status: {status}")
    assert status == 200, f"Failed to create user1: {res}"
    user1_id = res["id"]
    print(f"User1 ID: {user1_id}")

    print("\n--- 2. Creating user2 ---")
    status, res = make_request(
        f"{BASE_URL}/collections/users/records",
        "POST",
        {
            "email": "user2@example.com",
            "password": "password123456",
            "passwordConfirm": "password123456"
        }
    )
    print(f"Status: {status}")
    assert status == 200, f"Failed to create user2: {res}"
    user2_id = res["id"]
    print(f"User2 ID: {user2_id}")

    print("\n--- 3. Authenticating user1 ---")
    status, res = make_request(
        f"{BASE_URL}/collections/users/auth-with-password",
        "POST",
        {
            "identity": "user1@example.com",
            "password": "password123456"
        }
    )
    print(f"Status: {status}")
    assert status == 200, f"Failed to authenticate user1: {res}"
    token1 = res["token"]

    print("\n--- 4. Authenticating user2 ---")
    status, res = make_request(
        f"{BASE_URL}/collections/users/auth-with-password",
        "POST",
        {
            "identity": "user2@example.com",
            "password": "password123456"
        }
    )
    print(f"Status: {status}")
    assert status == 200, f"Failed to authenticate user2: {res}"
    token2 = res["token"]

    print("\n--- 5. Creating a post as user1 ---")
    status, res = make_request(
        f"{BASE_URL}/collections/posts/records",
        "POST",
        {
            "title": "My Post",
            "owner": user1_id
        },
        token=token1
    )
    print(f"Status: {status}")
    assert status == 200, f"Failed to create post: {res}"
    post_id = res["id"]
    print(f"Post ID: {post_id}")

    print("\n--- 6. Updating post title as user1 (should succeed) ---")
    status, res = make_request(
        f"{BASE_URL}/collections/posts/records/{post_id}",
        "PATCH",
        {
            "title": "My Updated Title"
        },
        token=token1
    )
    print(f"Status: {status}")
    assert status == 200, f"Failed to update title: {res}"
    assert res["title"] == "My Updated Title"
    print("Post title updated successfully!")

    print("\n--- 7. Attempting to update owner field of owned post (should fail with 400 or 403) ---")
    status, res = make_request(
        f"{BASE_URL}/collections/posts/records/{post_id}",
        "PATCH",
        {
            "owner": user2_id
        },
        token=token1
    )
    print(f"Status: {status}")
    print(f"Response: {res}")
    assert status in (400, 403), f"Expected 400 or 403, got {status}: {res}"
    print("Correctly prevented modifying owner field!")

    print("\n--- 8. Attempting to update post owned by user1 as user2 (should fail with 403 or 404) ---")
    status, res = make_request(
        f"{BASE_URL}/collections/posts/records/{post_id}",
        "PATCH",
        {
            "title": "Hacked Title"
        },
        token=token2
    )
    print(f"Status: {status}")
    print(f"Response: {res}")
    assert status in (403, 404), f"Expected 403 or 404, got {status}: {res}"
    print("Correctly prevented user2 from updating user1's post!")

    print("\nALL TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    try:
        run_tests()
    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
        sys.exit(1)
