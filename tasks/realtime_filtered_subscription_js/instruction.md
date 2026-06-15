# Filtered Realtime Subscription with the PocketBase JS SDK

## Goal
A PocketBase v0.31.0 server is already running locally with a pre-seeded `messages` collection (fields: `chat`, `body`). Build a Node.js CLI that uses the official `pocketbase` npm package (JS SDK) to open a realtime SSE subscription on the `messages` collection that only delivers events whose `chat` field equals the chat id passed on the command line.

## Acceptance Criteria
- Project path: /home/user/myproject
- Command: `node subscribe.js --chat <chatId>`
- PocketBase server URL: `http://127.0.0.1:8090`. Superuser credentials are available via the env vars `PB_ADMIN_EMAIL` and `PB_ADMIN_PASSWORD`.
- For every realtime event the script receives, it MUST write exactly one JSON object on its own line to stdout with the shape `{"action": "create|update|delete", "record": { ...record fields including id and chat... }}` and flush.
- Server-side filtering MUST be used so that events for records with a different `chat` value never reach stdout.
- When records are created in `messages` with `chat='A'`, `chat='B'`, `chat='A'` while the script is running with `--chat A`, the script MUST print exactly 2 JSON lines on stdout, each with `action: "create"` and `record.chat == "A"`, within 5 seconds of record creation. No event for `chat='B'` may appear.
- Nothing besides the JSON event lines may be written to stdout (logs/debug output must go to stderr or be suppressed).
- The script MUST exit with status 0 within 3 seconds when sent SIGTERM after subscribing successfully.

