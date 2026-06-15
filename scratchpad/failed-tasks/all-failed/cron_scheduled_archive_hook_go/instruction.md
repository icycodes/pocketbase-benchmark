# Scheduled Archive Job with Embedded PocketBase (Go)

## Background
You are building a small backend in Go that embeds PocketBase v0.31.0 as a library. The backend exposes the standard PocketBase REST API and runs a background scheduled job that periodically moves aging records from a primary `posts` collection into a separate `archive_posts` collection, preserving the original record id and adding an `archived_at` timestamp.

## Requirements
- The application MUST be a custom Go executable that imports `github.com/pocketbase/pocketbase` at version `v0.31.0` and exposes the standard PocketBase REST API.
- Two `base` collections must exist when the server is running:
  - `posts` with text fields `title` and `content`.
  - `archive_posts` with text fields `title`, `content` and a `date` (datetime) field named `archived_at`.
- Both collections must allow unauthenticated `list`, `view`, `create`, `update` and `delete` so the verifier can seed and inspect them via the public REST API.
- A scheduled job must be registered through the app-level cron service and must execute on every minute boundary while the server is running.
- On every tick the job MUST:
  - Determine an age threshold (in seconds) from the environment variable `ARCHIVE_AGE_SECONDS` (default 60 when unset or invalid).
  - For each record in `posts` whose creation time (`created`) is older than the threshold relative to the tick time, atomically (per record, inside a database transaction):
    1. Create a new record in `archive_posts` whose `id` equals the original `posts.id`, with the same `title` and `content`, and with `archived_at` set to the time the archive copy is written (ISO-8601, UTC).
    2. Delete the original record from `posts` in the same transaction so partial state can never be observed.
  - Records whose `created` time is newer than the threshold MUST be left untouched in `posts`.

## Implementation Hints
- Use the v0.31+ Go API: `pocketbase.New()`, hook registration through `BindFunc`, and the app-level cron service to register the job before `app.Start()`.
- The PocketBase Go module requires Go 1.23 or newer.
- Use the transaction-scoped app instance inside the cron handler when issuing the paired "save in archive / delete from source" writes — running both operations through the global app would risk an SQLite write deadlock.
- Collections can be provisioned at start time using a `core.BootstrapEvent` hook (run AFTER `e.Next()` so the system collections exist) or via Go migrations; either approach is acceptable as long as the collections exist by the time the server begins accepting requests.
- The verifier seeds records by `POST /api/collections/posts/records` and reads them back via `GET /api/collections/posts/records` and `GET /api/collections/archive_posts/records`; configure the collection access rules accordingly.
- A `run-id` is provided in the `ZEALT_RUN_ID` environment variable. The verifier tags every seeded post `title` with that id; your implementation does not need to read `ZEALT_RUN_ID` itself, but it must preserve `title` and `content` verbatim during archival so the verifier can find its records.

## Acceptance Criteria
- Project path: /home/user/myproject
- Start command: cd /home/user/myproject && ./myapp serve --http=0.0.0.0:8090
- Port: 8090
- REST endpoints exposed (standard PocketBase):
  - `GET /api/collections/posts/records`
  - `POST /api/collections/posts/records`
  - `GET /api/collections/archive_posts/records`
- Cron behavior:
  - A job runs on every minute boundary while the server is up.
  - Threshold is read from `ARCHIVE_AGE_SECONDS` (default 60).
  - After the server has been running for at least 90 seconds with `ARCHIVE_AGE_SECONDS=5`, every record that was created in `posts` more than 5 seconds before any cron tick must have moved to `archive_posts`:
    - The archive record's `id` equals the original `posts.id`.
    - `title` and `content` are byte-for-byte identical to the original.
    - `archived_at` is a valid ISO-8601 timestamp within 65 seconds of the original `created` time.
    - The original `posts` record with that id no longer exists.
  - Records that were younger than 5 seconds at every observed tick remain in `posts`.
- Atomicity: at no point may both the source `posts` row and its `archive_posts` copy exist simultaneously (and at no point may the source disappear without its copy being written).
- Collection access rules permit unauthenticated REST traffic for `list`, `view`, `create`, `update` and `delete` on both `posts` and `archive_posts`.

