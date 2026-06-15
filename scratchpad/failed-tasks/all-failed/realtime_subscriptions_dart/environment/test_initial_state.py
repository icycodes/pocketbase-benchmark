import os
import shutil
import subprocess
import time
import urllib.request
import urllib.error
import json

def test_dart_binary_available():
    assert shutil.which("dart") is not None, "dart binary not found in PATH."

def test_pocketbase_binary_available():
    assert os.path.isfile("/usr/local/bin/pocketbase"), "pocketbase binary not found at /usr/local/bin/pocketbase."

def test_pocketbase_server_running_and_setup():
    # Start PocketBase server in the background if it's not already running
    try:
        urllib.request.urlopen("http://127.0.0.1:8090/api/health", timeout=2)
    except Exception:
        # Start the server
        subprocess.Popen(
            ["/usr/local/bin/pocketbase", "serve", "--http=0.0.0.0:8090", "--dir=/pb/pb_data"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        # Wait for the server to be ready
        ready = False
        for _ in range(10):
            try:
                urllib.request.urlopen("http://127.0.0.1:8090/api/health", timeout=1)
                ready = True
                break
            except Exception:
                time.sleep(1)
        assert ready, "PocketBase server failed to start on port 8090."

    # Wait, we need to create an admin, then use the admin token to create the `posts` collection and a test user.
    # But wait! If the Dockerfile already sets up the pb_data via a migration or a pre-populated pb_data, we just need to verify it.
    # Let's assume the Dockerfile will set up the `posts` collection and a test user, and we just verify they exist.
    # Wait, the instruction says "If there is any background service that needs to run, start the service during the initial state test".
    # It does not say we should *create* the state in the test. We should test that the state exists.
    pass

def test_posts_collection_exists():
    # We can query the collections API. It requires admin auth, but we can just check if the collection exists by trying to list its records (which might be forbidden, but returns 403 instead of 404).
    try:
        req = urllib.request.Request("http://127.0.0.1:8090/api/collections/posts/records")
        urllib.request.urlopen(req)
        exists = True
    except urllib.error.HTTPError as e:
        # 400 or 403 means the collection exists but we don't have permission or query is wrong. 404 means it doesn't exist.
        exists = e.code != 404
    except Exception:
        exists = False
    
    assert exists, "The 'posts' collection does not exist in PocketBase."
