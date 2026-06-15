# PocketBase v0.31.0 Go Migration with Seed Data

## Goal
Build a custom Go PocketBase v0.31.0 binary that ships exactly ONE reversible Go migration which creates two collections (`categories`, `articles`) and seeds them with deterministic initial data. The down step must remove both collections and the seeded records.

## Acceptance Criteria
- Project path: /home/user/myproject
- Binary path: /home/user/myproject/app
- Build command: `go build -o /home/user/myproject/app .` (executed in /home/user/myproject)
- Migrate up command: `/home/user/myproject/app migrate up`
- Migrate down command: `/home/user/myproject/app migrate down 1`
- Serve command: `/home/user/myproject/app serve --http=0.0.0.0:8090`
- Port: 8090
- After `./app migrate up`:
  - `GET http://localhost:8090/api/collections/categories/records` returns HTTP 200 with `totalItems = 3` and the `items[].name` values are exactly the set {`Tech`, `Life`, `News`} (order not enforced).
  - `GET http://localhost:8090/api/collections/articles/records` returns HTTP 200 with `totalItems = 6` and every `items[].category` value equals the `id` of one of the three category records.
  - Each article record contains non-empty `title` and `body` string fields.
  - The `category` field on `articles` is a single relation to `categories`, required, with cascade delete behavior.
  - The `name` field on `categories` is unique.
- After `./app migrate down 1` (run once after a successful up):
  - Both `categories` and `articles` collections are absent: `GET /api/collections/categories/records` and `GET /api/collections/articles/records` both return HTTP 404.
- After running `./app migrate up` again following the down:
  - The same 3 categories (`Tech`, `Life`, `News`) and exactly 6 articles are restored deterministically.

