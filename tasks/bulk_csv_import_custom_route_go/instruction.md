# Bulk CSV Import Custom Route (PocketBase Go)

## Goal
Implement a Go-embedded PocketBase v0.31.0 application that exposes a superuser-only custom route `POST /api/import/products` for bulk-importing products from a CSV file. All inserts must be performed inside a single database transaction; if any row fails validation, the entire batch must be rolled back.

## Acceptance Criteria
- Project path: /home/user/myproject
- Start command: `./myapp serve --http=0.0.0.0:8090` (the binary is produced by `go build -o myapp .` inside the project directory).
- Port: 8090
- A `base` collection named `products` with the fields `sku` (text), `name` (text) and `price` (number) must exist after the server has started.
- Route: `POST /api/import/products`
  - Must require superuser authentication (`Authorization: Bearer <superuser-token>`).
  - Accepts a `multipart/form-data` request with a single file field named `file` containing a CSV whose first row is the header `sku,name,price`.
  - Validates every data row: `price` must be > 0, `sku` must be unique within the uploaded file, and `sku` must not already exist in the `products` collection.
  - All inserts must run inside a single transaction. If ANY row fails validation, the transaction must be rolled back so that no new records are inserted.
  - Success response: HTTP 200 with JSON body `{"inserted": <int>, "errors": []}`.
  - Validation-failure response: HTTP 400 with JSON body `{"inserted": 0, "errors": [{"row": <int>, "reason": <string>}, ...]}` where `row` is the 1-based row number of the offending data row (the header is not counted).
  - Unauthenticated request: HTTP 401.
  - Authenticated, non-superuser request: HTTP 403.

## Credentials (pre-provisioned)
- Superuser: `$PB_SUPERUSER_EMAIL` / `$PB_SUPERUSER_PASSWORD` (already exists in the `pb_data/` directory packaged with the environment).
- A regular auth user is provisioned by the verifier at test time; do not hard-code regular-user credentials.

