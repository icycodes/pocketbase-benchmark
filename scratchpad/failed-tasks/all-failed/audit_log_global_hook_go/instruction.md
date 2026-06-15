# Audit Log via Global Hooks (PocketBase v0.31.0, Go)

## Goal
Build a Go PocketBase v0.31.0 application that registers global event hooks covering record create/update/delete across ALL non-system collections, writing one row per successful mutation to a dedicated `audit_log` collection.

## Acceptance Criteria
- Project path: /home/user/myproject
- The PocketBase Go module `github.com/pocketbase/pocketbase@v0.31.0` is used.
- Build command: `go build -o app .`
- Start command: `./app serve --http=0.0.0.0:8090`
- Port: 8090
- The `posts` collection (base) exists with at least a `title` (text) field.
- The `audit_log` collection (base) exists with these fields:
  - `actor` (text)
  - `action` (text)
  - `collection` (text)
  - `record` (text)
  - `at` (date)
  - `diff` (json)
- For every successful create/update/delete mutation on a non-system collection, the app inserts exactly one row into the `audit_log` collection with the following semantics:
  - `actor`: the authenticated user id, or the string `anon` when there is no authenticated user.
  - `action`: one of `create`, `update`, `delete`.
  - `collection`: the name of the mutated record's collection.
  - `record`: the id of the mutated record.
  - `at`: the timestamp of the audit row.
  - `diff`: for `update`, a JSON object containing ONLY changed fields with the exact shape `{"<field>":{"old":<old_value>,"new":<new_value>}, ...}`. For `create` and `delete`, the value is an empty JSON object `{}`.
- Mutations on the `audit_log` collection itself MUST NOT generate any audit rows (no infinite loops).
- Mutations on PocketBase system collections (collection names starting with `_`, e.g. `_superusers`) MUST NOT generate audit rows.
- Verification scenario: After authenticating as a regular user and performing, in order, (1) create a `posts` record with `title="Original Title"`, (2) update that record changing ONLY `title` to `"Updated Title"`, (3) delete that record, the `audit_log` collection MUST contain exactly 3 new rows referencing the created post id, in this chronological order:
  1. `action=create`, `collection=posts`, `record=<posts_id>`, `actor=<user_id>`, `diff={}`
  2. `action=update`, `collection=posts`, `record=<posts_id>`, `actor=<user_id>`, `diff={"title":{"old":"Original Title","new":"Updated Title"}}` (exactly this object, no other keys)
  3. `action=delete`, `collection=posts`, `record=<posts_id>`, `actor=<user_id>`, `diff={}`
- After the scenario above, the count of `audit_log` rows where `collection="audit_log"` MUST be 0.

