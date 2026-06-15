# S3 Presigned Upload Routes for PocketBase (Go)

## Goal
Build a custom PocketBase v0.31.0 backend in Go that exposes two authenticated REST endpoints used by clients to upload files directly to an S3-compatible object store (local MinIO). The backend itself must never proxy the file bytes — it only mints short-lived presigned URLs and tracks pending vs. finalized uploads in its own SQLite collections.

## Acceptance Criteria
- Project path: `/home/user/myapp`
- Start command: `./myapp serve --http=0.0.0.0:8090` (the executable named `myapp` must be produced by `go build` in the project directory; the verifier will (re)build it if missing).
- Port: `8090`
- The PocketBase application must use the `github.com/pocketbase/pocketbase` module at version `v0.31.0`.
- A pre-seeded superuser is available for collection bootstrapping: `admin@example.com` / `1234567890`.
- A pre-seeded regular auth user lives in the `users` collection: `user@example.com` / `password1234`.
- A second regular auth user lives in the `users` collection: `other@example.com` / `password1234`.
- The S3-compatible target is a local MinIO server reachable at `http://127.0.0.1:9000` with credentials `minioadmin` / `minioadmin`, region `us-east-1`, and a pre-created bucket named `uploads`. The Go process may read these from any environment variables it chooses, but the defaults above MUST work out of the box when the variables are unset.
- Two collections MUST exist (the app may create them programmatically on boot or via migrations):
  - `pending_upload` (type `base`) with fields:
    - `user` (relation to `users`, required, single)
    - `key` (text, required, unique)
    - `expires_at` (date, required)
  - `uploads` (type `base`) with fields:
    - `user` (relation to `users`, required, single)
    - `key` (text, required, unique)
- Endpoint `POST /api/uploads/presign`:
  - Requires a valid PocketBase auth token from the `users` collection. Unauthenticated requests MUST return HTTP `401`.
  - On success returns HTTP `200` with JSON body containing AT LEAST the fields:
    - `url` — a presigned S3 PUT URL whose host/path resolves to `http(s)://<minio-host>:<port>/uploads/<key>?...` (path-style addressing, with AWS SigV4 query parameters such as `X-Amz-Signature`).
    - `key` — a server-generated object key (must look like a UUID, i.e. match `^[a-f0-9-]{16,}$`).
    - `expiresAt` — an RFC3339 timestamp at least 299 seconds in the future and at most 360 seconds in the future at the moment the response is produced.
  - The presigned URL MUST be valid for exactly 300 seconds (±5s tolerance) and MUST allow an HTTP `PUT` with arbitrary body to upload the object to the `uploads` bucket under the returned `key`.
  - Before returning, the handler MUST create a record in `pending_upload` whose `user` equals the authenticated user's id, `key` equals the returned `key`, and `expires_at` equals the returned `expiresAt`.
- Endpoint `POST /api/uploads/finalize`:
  - Requires a valid PocketBase auth token from the `users` collection. Unauthenticated requests MUST return HTTP `401`.
  - Accepts JSON body `{ "key": "<key>" }`.
  - The handler MUST verify the object exists in the bucket via an S3 `HEAD` request. If the object does not exist, respond with HTTP `404`.
  - If a `pending_upload` record for the given `key` does not exist OR belongs to a different user, respond with HTTP `404`.
  - On success: delete the `pending_upload` row for that `key`, create a new `uploads` row with the same `user` and `key`, and respond with HTTP `200` and a JSON body that contains at least `{ "key": "<key>" }`.
- The two endpoints MUST live under `/api/uploads/...` exactly as written above so the verifier can reach them.
- The app may emit logs to stdout/stderr; no specific log format is required.

