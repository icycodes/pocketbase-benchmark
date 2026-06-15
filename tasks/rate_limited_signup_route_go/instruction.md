# Per-IP Rate-Limited Signup on PocketBase

## Goal
Configure PocketBase v0.31.0 so that the user-signup endpoint `POST /api/collections/users/records` enforces a per-IP rate limit of 3 requests per 60 seconds. Excess requests must be rejected with a custom 429 response.

## Acceptance Criteria
- Project path: /home/user/myproject
- Start command: bash /home/user/myproject/start.sh
- Port: 8090
- PocketBase v0.31.0 must be reachable at http://127.0.0.1:8090 and expose the built-in `users` auth collection.
- The first 3 calls to `POST /api/collections/users/records` from the same client IP within any rolling 60-second window must be processed normally (the server may answer with status 200/201 for valid payloads or 400 for validation failures, but MUST NOT answer with 429).
- The 4th call from the same IP within that 60-second window must return HTTP status `429` with:
  - A response header `Retry-After` whose value is a positive integer (seconds, `>= 1`).
  - A JSON response body that contains a top-level field `retryAfter` whose numeric value equals the `Retry-After` header value within ±2 seconds.
- After waiting for the number of seconds advertised by `Retry-After`, a subsequent (5th) signup attempt from the same IP must again succeed (status 200/201 for a valid payload, or 400 for validation; not 429).
- Other endpoints, e.g. `GET /api/collections/users/records`, MUST NOT be rate-limited by this rule: at least 10 consecutive GETs from the same IP within the same window must each return a non-`429` status.
- The `users` collection's create rule must allow unauthenticated signup using JSON body `{ "email": "...", "password": "...", "passwordConfirm": "..." }` (i.e. open signup; the signup endpoint itself must be reachable without auth).

