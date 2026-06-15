# Concurrent Wallet Transfer Endpoint

## Goal
A Go project that embeds PocketBase v0.31.0 is already scaffolded at `/home/user/myproject` with `wallets` and `transfers` collections seeded. Extend it so that authenticated users can move money between wallets via `POST /api/wallets/transfer` (body `{ "fromId": string, "toId": string, "amount": number }`) and the endpoint survives heavy concurrent load against the single-writer SQLite store.

## Acceptance Criteria
- Project path: /home/user/myproject
- Start command: /home/user/myproject/myapp serve --http="0.0.0.0:8090" --dir=/home/user/myproject/pb_data
- Port: 8090
- API Endpoints:
  - `POST /api/wallets/transfer` (requires `Authorization: <user-token>`):
    - Request body:
      ```json
      { "fromId": string, "toId": string, "amount": number }
      ```
    - Success response (HTTP 200):
      ```json
      { "fromBalance": number, "toBalance": number }
      ```
    - Insufficient-funds response (HTTP 400): JSON with an error message; wallet balances unchanged.
  - Unauthenticated requests must be rejected (HTTP 401 or 403).
- Concurrency behavior: running 50 concurrent `$1` transfers from wallet A (initial balance 100) to wallet B (initial balance 0) using 10 worker threads must return HTTP 200 for every request, leave final A.balance == 50 and B.balance == 50, insert exactly 50 rows into the `transfers` collection, and complete in under 30 seconds without deadlock.

