# SvelteKit + PocketBase SSR Cookie Auth Sync Middleware

## Goal
In the existing SvelteKit project at `/home/user/myproject`, build a server-side middleware that synchronizes PocketBase auth state across SSR requests using the `pb_auth` cookie, and expose a `GET /api/whoami` route that reports the current authenticated user.

A PocketBase v0.31.0 server is already running at `http://127.0.0.1:8090` with a seeded user in its `users` collection.

## Acceptance Criteria
- Project path: /home/user/myproject
- Start command: npm run preview -- --host 0.0.0.0 --port 4173
- Port: 4173
- The SvelteKit app, after running `npm run build`, must serve the routes described below from its preview server.
- `GET /api/whoami` without any cookies:
    - Returns HTTP 200 with JSON body exactly `{"user": null}`.
- `GET /api/whoami` with a valid `pb_auth` cookie produced by authenticating against `POST http://127.0.0.1:8090/api/collections/users/auth-with-password`:
    - Returns HTTP 200 with JSON body of the shape `{"user": {"id": string, "email": string}}` matching the authed user.
    - The response includes a `Set-Cookie` header for the `pb_auth` cookie whose embedded JWT has an `exp` claim strictly greater than the `exp` claim of the request cookie's JWT (the token has been refreshed).
- `GET /api/whoami` with an expired or otherwise invalid `pb_auth` cookie:
    - Returns HTTP 200 with JSON body exactly `{"user": null}`.
    - The response includes a `Set-Cookie` header for the `pb_auth` cookie that clears the cookie on the client (empty token payload, or `Max-Age=0`, or `Expires` in the past).

