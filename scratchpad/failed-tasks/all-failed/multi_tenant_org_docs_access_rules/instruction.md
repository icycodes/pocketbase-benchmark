# Multi-Tenant Documents Access Rules in PocketBase

## Background
A PocketBase v0.31.0 server is preinstalled in the project directory. You need to configure a multi-tenant document collaboration backend where each organization is an isolated tenant and access to documents is governed by per-organization memberships and roles.

## Requirements
Configure the running PocketBase instance so that, in addition to the default `users` auth collection, it exposes three base collections that implement multi-tenant access control:

- `organizations` — fields: `name` (text, required).
- `memberships` — fields: `org` (relation → `organizations`, required, single), `user` (relation → `users`, required, single), `role` (single-select with the exact options `viewer` and `editor`, required).
- `documents` — fields: `org` (relation → `organizations`, required, single), `title` (text, required), `content` (text).

Define the API access rules on the `documents` collection so that:
- An authenticated user may list or view a document only if they have a `memberships` record linking them to that document's `org`.
- An authenticated user may create a document for an organization only if they have a `memberships` record in that organization with the role `editor`.
- An authenticated user may update a document only if they have a `memberships` record in that document's organization with the role `editor`.
- No client (including an editor) may modify the `org` field of an existing document.
- Guests (unauthenticated requests) must not be able to list, view, create, or update any document.

## Implementation Hints
- PocketBase v0.31.0 is already extracted at the project path. Use its built-in collections/migrations mechanism and API rule expressions to satisfy the requirements.
- The verifier will only inspect the externally observable HTTP behavior of the documents API; it will not look at how the configuration is achieved.

## Acceptance Criteria
- Project path: /home/user/myproject
- Start command: ./pocketbase serve --http=0.0.0.0:8090 --dir=./pb_data --migrationsDir=./pb_migrations
- Port: 8090
- A bootstrapped superuser with email `admin@example.com` and password `Adm1n_Password!` must be usable to authenticate via `POST /api/collections/_superusers/auth-with-password`.
- The collections `organizations`, `memberships`, and `documents` must exist with the field names and types listed in Requirements; `memberships.role` must be a single-select field whose only allowed option values are exactly `viewer` and `editor`.
- API behavior of `/api/collections/documents/records` after the configuration is applied:
  - Authenticated `GET /api/collections/documents/records` returns only documents whose `org` matches an organization the caller has a `memberships` record for; documents in other organizations must not appear in the response items.
  - Authenticated `GET /api/collections/documents/records/{id}` for a document whose `org` the caller is NOT a member of must return HTTP 404.
  - Authenticated `GET /api/collections/documents/records/{id}` for a document whose `org` the caller IS a member of (any role) must return HTTP 200 with the record.
  - Authenticated `POST /api/collections/documents/records` with a target `org` must return HTTP 200 only when the caller has a `memberships` record for that `org` with role `editor`; otherwise it must fail with HTTP 400 or 403.
  - Authenticated `PATCH /api/collections/documents/records/{id}` must return HTTP 200 only when the caller has a `memberships` record for that document's `org` with role `editor`; viewers must receive HTTP 404 and non-members must receive HTTP 404.
  - Authenticated `PATCH /api/collections/documents/records/{id}` that attempts to set the `org` field to a different organization (even when the caller is an editor of the document's current `org`) must NOT succeed — the response must be an error (HTTP 400 or 403) and the stored `org` value must remain unchanged.
  - Unauthenticated `GET`, `POST`, or `PATCH` requests to `/api/collections/documents/records[...]` must NOT succeed and must not return any document data.
- All behavior must be observable via the standard PocketBase REST API on port 8090 without any custom routes.

