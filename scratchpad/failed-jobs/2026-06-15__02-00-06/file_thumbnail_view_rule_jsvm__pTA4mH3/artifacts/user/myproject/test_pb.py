import requests
import io

BASE_URL = "http://localhost:8090"

def run_tests():
    # 1. Log in as superuser
    print("Logging in as superuser...")
    r = requests.post(f"{BASE_URL}/api/collections/_superusers/auth-with-password", json={
        "identity": "admin@example.com",
        "password": "Admin12345!"
    })
    if r.status_code != 200:
        print(f"Failed to log in as superuser: {r.status_code} {r.text}")
        return
    admin_token = r.json()["token"]
    print("Superuser login successful.")

    # 2. Check if users exist or create them
    # Let's create user1
    print("Creating user1...")
    r = requests.post(f"{BASE_URL}/api/collections/users/records", json={
        "email": "user1@example.com",
        "password": "Password12345!",
        "passwordConfirm": "Password12345!",
        "emailVisibility": True
    }, headers={"Authorization": f"Bearer {admin_token}"})
    if r.status_code in (200, 201):
        user1_id = r.json()["id"]
        print(f"Created user1: {user1_id}")
    else:
        # Maybe already exists, let's find it
        print("user1 might already exist, fetching users...")
        r = requests.get(f"{BASE_URL}/api/collections/users/records?filter=(email='user1@example.com')", headers={"Authorization": f"Bearer {admin_token}"})
        user1_id = r.json()["items"][0]["id"]
        print(f"Found user1: {user1_id}")

    # Create user2
    print("Creating user2...")
    r = requests.post(f"{BASE_URL}/api/collections/users/records", json={
        "email": "user2@example.com",
        "password": "Password12345!",
        "passwordConfirm": "Password12345!",
        "emailVisibility": True
    }, headers={"Authorization": f"Bearer {admin_token}"})
    if r.status_code in (200, 201):
        user2_id = r.json()["id"]
        print(f"Created user2: {user2_id}")
    else:
        print("user2 might already exist, fetching users...")
        r = requests.get(f"{BASE_URL}/api/collections/users/records?filter=(email='user2@example.com')", headers={"Authorization": f"Bearer {admin_token}"})
        user2_id = r.json()["items"][0]["id"]
        print(f"Found user2: {user2_id}")

    # 3. Log in as user1 and user2
    print("Logging in as user1...")
    r = requests.post(f"{BASE_URL}/api/collections/users/auth-with-password", json={
        "identity": "user1@example.com",
        "password": "Password12345!"
    })
    user1_token = r.json()["token"]

    print("Logging in as user2...")
    r = requests.post(f"{BASE_URL}/api/collections/users/auth-with-password", json={
        "identity": "user2@example.com",
        "password": "Password12345!"
    })
    user2_token = r.json()["token"]

    # 4. Generate small 1x1 PNG image bytes
    # 1x1 transparent PNG image bytes
    png_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDAT\x08\xd7c`\x00\x00\x00\x02\x00\x01\xe2(\xbc3\x00\x00\x00\x00IEND\xaeB`\x82'

    # 5. Upload private photo as user1
    print("Uploading private photo as user1...")
    files = {"image": ("private.png", io.BytesIO(png_bytes), "image/png")}
    data = {"owner": user1_id, "is_public": "false"}
    r = requests.post(f"{BASE_URL}/api/collections/photos/records", files=files, data=data, headers={"Authorization": f"Bearer {user1_token}"})
    if r.status_code not in (200, 201):
        print(f"Failed to upload private photo: {r.status_code} {r.text}")
        return
    private_record = r.json()
    private_id = private_record["id"]
    private_filename = private_record["image"]
    print(f"Uploaded private photo: record={private_id}, file={private_filename}")

    # 6. Upload public photo as user1
    print("Uploading public photo as user1...")
    files = {"image": ("public.png", io.BytesIO(png_bytes), "image/png")}
    data = {"owner": user1_id, "is_public": "true"}
    r = requests.post(f"{BASE_URL}/api/collections/photos/records", files=files, data=data, headers={"Authorization": f"Bearer {user1_token}"})
    if r.status_code not in (200, 201):
        print(f"Failed to upload public photo: {r.status_code} {r.text}")
        return
    public_record = r.json()
    public_id = public_record["id"]
    public_filename = public_record["image"]
    print(f"Uploaded public photo: record={public_id}, file={public_filename}")

    # 7. Get File Tokens
    print("Generating file tokens...")
    r = requests.post(f"{BASE_URL}/api/files/token", headers={"Authorization": f"Bearer {user1_token}"})
    user1_file_token = r.json()["token"]
    r = requests.post(f"{BASE_URL}/api/files/token", headers={"Authorization": f"Bearer {user2_token}"})
    user2_file_token = r.json()["token"]

    print("\n--- STARTING TESTS ---")

    # TEST 1: Unsupported thumb size (e.g. 200x200), regardless of auth
    # Expected: 400 Bad Request, exactly {"message":"unsupported thumb"}
    url = f"{BASE_URL}/api/files/photos/{private_id}/{private_filename}?thumb=200x200"
    r = requests.get(url)
    print(f"TEST 1a (unauth, unsupported thumb): status={r.status_code}, body={r.text}")
    assert r.status_code == 400, f"Expected 400, got {r.status_code}"
    assert r.json() == {"message": "unsupported thumb"}, f"Expected exact body, got {r.text}"

    r = requests.get(url, headers={"Authorization": f"Bearer {user1_token}"})
    print(f"TEST 1b (user1 auth, unsupported thumb): status={r.status_code}, body={r.text}")
    assert r.status_code == 400, f"Expected 400, got {r.status_code}"
    assert r.json() == {"message": "unsupported thumb"}, f"Expected exact body, got {r.text}"

    # TEST 2: Supported thumb size 100x100 for private photo
    # Expected: 200 for owner (user1), 403 for non-owner (user2), 403 for unauth
    url_100 = f"{BASE_URL}/api/files/photos/{private_id}/{private_filename}?thumb=100x100"
    
    # 2a: unauth
    r = requests.get(url_100)
    print(f"TEST 2a (unauth, private, 100x100): status={r.status_code}")
    assert r.status_code == 403, f"Expected 403, got {r.status_code}"

    # 2b: user1 (owner) via Authorization header
    r = requests.get(url_100, headers={"Authorization": f"Bearer {user1_token}"})
    print(f"TEST 2b (user1 direct auth, private, 100x100): status={r.status_code}, content-type={r.headers.get('content-type')}")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    assert r.headers.get("content-type", "").startswith("image/"), "Expected image/ content-type"

    # 2c: user1 (owner) via token query param
    r = requests.get(f"{url_100}&token={user1_file_token}")
    print(f"TEST 2c (user1 token, private, 100x100): status={r.status_code}, content-type={r.headers.get('content-type')}")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    assert r.headers.get("content-type", "").startswith("image/"), "Expected image/ content-type"

    # 2d: user2 (non-owner) via Authorization header
    r = requests.get(url_100, headers={"Authorization": f"Bearer {user2_token}"})
    print(f"TEST 2d (user2 direct auth, private, 100x100): status={r.status_code}")
    assert r.status_code == 403, f"Expected 403, got {r.status_code}"

    # 2e: user2 (non-owner) via token query param
    r = requests.get(f"{url_100}&token={user2_file_token}")
    print(f"TEST 2e (user2 token, private, 100x100): status={r.status_code}")
    assert r.status_code == 403, f"Expected 403, got {r.status_code}"

    # TEST 3: Supported thumb size 400x300t for public photo
    # Expected: 200 for everyone (owner, non-owner, unauth)
    url_400_pub = f"{BASE_URL}/api/files/photos/{public_id}/{public_filename}?thumb=400x300t"

    # 3a: unauth
    r = requests.get(url_400_pub)
    print(f"TEST 3a (unauth, public, 400x300t): status={r.status_code}, content-type={r.headers.get('content-type')}")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    assert r.headers.get("content-type", "").startswith("image/"), "Expected image/ content-type"

    # 3b: user2 (non-owner)
    r = requests.get(url_400_pub, headers={"Authorization": f"Bearer {user2_token}"})
    print(f"TEST 3b (user2 direct auth, public, 400x300t): status={r.status_code}, content-type={r.headers.get('content-type')}")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    assert r.headers.get("content-type", "").startswith("image/"), "Expected image/ content-type"

    # TEST 4: Original file (no thumb) for private photo
    # Expected: 200 for owner (user1), 403 for non-owner (user2)
    url_orig_priv = f"{BASE_URL}/api/files/photos/{private_id}/{private_filename}"

    # 4a: unauth
    r = requests.get(url_orig_priv)
    print(f"TEST 4a (unauth, private, original): status={r.status_code}")
    assert r.status_code == 403, f"Expected 403, got {r.status_code}"

    # 4b: user1 (owner)
    r = requests.get(url_orig_priv, headers={"Authorization": f"Bearer {user1_token}"})
    print(f"TEST 4b (user1 direct auth, private, original): status={r.status_code}")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"

    # 4c: user2 (non-owner)
    r = requests.get(url_orig_priv, headers={"Authorization": f"Bearer {user2_token}"})
    print(f"TEST 4c (user2 direct auth, private, original): status={r.status_code}")
    assert r.status_code == 403, f"Expected 403, got {r.status_code}"

    # TEST 5: Original file (no thumb) for public photo
    # Expected: 200 for everyone
    url_orig_pub = f"{BASE_URL}/api/files/photos/{public_id}/{public_filename}"

    # 5a: unauth
    r = requests.get(url_orig_pub)
    print(f"TEST 5a (unauth, public, original): status={r.status_code}")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"

    print("\nALL TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
