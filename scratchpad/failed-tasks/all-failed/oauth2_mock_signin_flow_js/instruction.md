# OAuth2 Sign-in Flow against a Mock Provider (PocketBase + JS SDK)

## Goal

Inside `/home/user/myproject`, configure the PocketBase `users` auth collection to
accept a custom OAuth2 provider whose endpoints point at the local mock OAuth2
server, and write a Node.js CLI script `app.js` that drives the full server-side
OAuth2 authorization-code sign-in using the official PocketBase JavaScript SDK and
prints the resulting `users` record as JSON on stdout.

PocketBase v0.31.0 is already running at `$PB_URL`, the mock OAuth2 server is
already running at `$MOCK_OAUTH_URL`, and superuser credentials are exposed via
`$PB_SUPERUSER_EMAIL` / `$PB_SUPERUSER_PASSWORD`.

## Acceptance Criteria

- Project path: `/home/user/myproject`
- Command: `node app.js`
- Running `node app.js` exits with status `0` and prints a single JSON object on
  stdout representing the authenticated `users` record, with:
  - a non-empty string `id`
  - `email == "oauth-user@example.com"`
  - `verified == true`
- After the command finishes, querying `GET /api/collections/users/records` as the
  superuser shows the user, and the `_externalAuths` system collection shows the
  user is linked to the configured custom OAuth2 provider (the one whose
  `displayName` is `mockoauth`) with a non-empty `providerId`.
