# Per-Authenticated-User Realtime Filtering in PocketBase

## Goal
In the PocketBase project at `/home/user/myproject`, configure a `notifications` collection so that PocketBase's realtime Server-Sent Events (SSE) stream naturally delivers notification records only to the user named on the record. JSVM hooks at `pb_hooks/*.pb.js` may be used as a supporting mechanism, but the primary filtering MUST be enforced by collection API rules so that a generic SSE subscriber sees only the records it is authorized to see.

## Acceptance Criteria
- Project path: `/home/user/myproject`
- Start command (run from the project path): `./pocketbase serve --http=0.0.0.0:8090`
- Port: `8090`
- A non-auth, non-view base collection named `notifications` exists with at least the following fields:
  - `recipient`: relation to the built-in `users` collection, required, single (`maxSelect = 1`).
  - `message`: text.
- The `notifications` collection's `listRule` and `viewRule` are BOTH the exact expression `recipient = @request.auth.id` (other rules — create/update/delete — may stay restricted to superusers).
- The pre-seeded `users` collection still contains the two regular accounts `alice@example.com` and `bob@example.com` (passwords pre-provisioned in `pb_data`). The verifier authenticates with these credentials via `POST /api/collections/users/auth-with-password`.
- Realtime SSE behavior on `GET /api/realtime` followed by `POST /api/realtime` with `subscriptions = ["notifications"]`:
  - When the subscriber sends an `Authorization` header for user A and the verifier creates three `notifications` records with recipients `[A, B, A]` via the superuser REST API, A's SSE stream MUST receive exactly two `create` messages within 5 seconds, and for every received message `record.recipient` MUST equal A's id.
  - When the subscriber sends an `Authorization` header for user B in the same scenario, B's SSE stream MUST receive exactly one `create` message within 5 seconds, with `record.recipient` equal to B's id.
  - When the subscriber sends NO `Authorization` header (anonymous), it MUST receive zero `create` messages for the `notifications` collection within 5 seconds.

