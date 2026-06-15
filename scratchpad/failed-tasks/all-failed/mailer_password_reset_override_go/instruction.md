# PocketBase Go Mailer Hook: Override Password Reset Email

## Goal
Build a Go PocketBase v0.31.0 application that intercepts the password-reset email for the built-in `users` collection and replaces the default Subject and HTML body with custom branded content, while still delivering through the configured SMTP server.

## Acceptance Criteria
- Project path: `/home/user/myapp`
- Start command: `cd /home/user/myapp && go run . serve --http=0.0.0.0:8090` (the verifier will (re)start this if not already running).
- Port: `8090` (PocketBase HTTP API).
- A real PocketBase v0.31.0 Go application (imports `github.com/pocketbase/pocketbase@v0.31.0`) running on port 8090 with the customized mailer hook registered.
- SMTP must be configured to deliver outbound mail to the local Mailpit instance on `localhost:1025` (Mailpit HTTP UI/API on `localhost:8025`).
- The `users` auth collection must contain a verified, seeded user whose credentials are provided through environment variables `TEST_USER_EMAIL` and `TEST_USER_NAME` (default value: `alice@example.com` / `Alice`).
- API behavior:
  - `POST /api/collections/users/request-password-reset` with body `{"email": "<TEST_USER_EMAIL>"}` returns HTTP `204` and causes exactly one email to be queued by Mailpit (`GET http://localhost:8025/api/v1/messages`).
  - The queued message:
    - `Subject` is **exactly** `Reset your acme.com password`.
    - `To` contains the original recipient address (`<TEST_USER_EMAIL>`); the recipient must not be rewritten.
    - HTML body is exactly of the form `Hi <NAME>! Use this link: <LINK>` where:
      - `<NAME>` is the value of `e.Record.GetString("name")`, or the user's email when the `name` field is empty.
      - `<LINK>` starts with `https://acme.com/reset?token=` and the `token` query parameter is the password-reset action token (a JWT in `header.payload.signature` form) that PocketBase generates for that send.
- The hook handler must call `e.Next()` so the underlying mailer still actually delivers the message via SMTP.

