# Password Strength Validator (PocketBase JSVM Hook)

## Goal
Implement a JSVM hook at `/home/user/pb-app/pb_hooks/users.pb.js` that enforces a password-strength policy whenever a record is created or updated in the `users` auth collection of the already-running PocketBase v0.31.0 server.

## Acceptance Criteria
- Project path: /home/user/pb-app
- Hook file path: /home/user/pb-app/pb_hooks/users.pb.js
- Start command: PocketBase v0.31.0 is already started by the container entrypoint and listens on port 8090 (HTTP).
- Port: 8090
- The hook MUST be wired so that it runs for BOTH record create and record update of the `users` auth collection.
- Password policy (applied to the plaintext password supplied in the request):
  - Length ≥ 12 characters
  - At least one uppercase ASCII letter (A-Z)
  - At least one lowercase ASCII letter (a-z)
  - At least one digit (0-9)
  - At least one symbol from the set `!@#$%^&*`
  - MUST NOT contain the user's email local-part (the substring before `@`), compared case-insensitively
- API behavior on `POST /api/collections/users/records`:
  - A request whose `password` satisfies every rule above MUST succeed with HTTP status `200` and create the user record (the hook must propagate execution).
  - A request that violates any rule MUST be rejected with HTTP status `400` and a JSON response whose body has a field-level error under the `password` field carrying a `code` selected from the table below:
    - `PWD_LEN` — password shorter than 12 characters
    - `PWD_UPPER` — missing uppercase letter
    - `PWD_LOWER` — missing lowercase letter
    - `PWD_DIGIT` — missing digit
    - `PWD_SYMBOL` — missing required symbol from `!@#$%^&*`
    - `PWD_CONTAINS_EMAIL` — password contains the email local-part (case-insensitive)
  - The response JSON MUST be readable as `response_json["data"]["password"]["code"]` for every violation case.
- The hook MUST call `e.next()` on the success path so valid creates/updates proceed and are persisted.

