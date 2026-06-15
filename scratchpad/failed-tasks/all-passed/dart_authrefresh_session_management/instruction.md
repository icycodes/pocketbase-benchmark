# Dart PocketBase CLI: Persisted Session with authRefresh

## Goal
Build a standalone Dart CLI at `/home/user/myproject` that authenticates against the local PocketBase v0.31.0 server (`http://127.0.0.1:8090`, `users` collection), persists the resulting auth token to a `session.json` file in the current working directory, and on subsequent runs refreshes that token using the official `pocketbase` pub package.

A seed user is already provisioned: `user@example.com` / `password`.

## Acceptance Criteria
- Entrypoint: `bin/app.dart`, runnable via `dart run bin/app.dart ...` from `/home/user/myproject`.
- `dart run bin/app.dart login <email> <password>`
  - Writes `session.json` (in the current working directory) containing a non-empty PocketBase auth token.
  - Exits 0.
- `dart run bin/app.dart refresh`
  - Loads `session.json`, calls `authRefresh()` on the `users` collection, and persists the new token back to `session.json` if it changed.
  - Stdout prints exactly two lines and nothing else: the authenticated user record id, then the token's `exp` claim as an integer epoch (seconds).
  - Exits 0.
- `dart run bin/app.dart refresh` with a corrupted `session.json` (not valid JSON or missing the token):
  - Prints exactly `INVALID_SESSION` to stderr.
  - Exits 1.
