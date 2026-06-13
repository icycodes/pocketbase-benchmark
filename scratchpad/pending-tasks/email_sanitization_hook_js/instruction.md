# PocketBase JSVM Email Sanitization Hook

## Background
[PocketBase](https://pocketbase.io/) is a single-file Go backend that can be extended with server-side JavaScript using scripts placed inside a `pb_hooks/` directory. The runtime is based on Goja (ECMAScript 5.1) and executes hooks synchronously.

A PocketBase v0.31.0 binary has been pre-extracted to `/home/user/myproject/pocketbase` and an initial superuser has been created so that the application is fully bootstrapped. Your job is to add a JavaScript hook that automatically sanitizes the `email` field on every new user-record creation request and then start the server.

## Requirements
- Add a JavaScript hook file inside `/home/user/myproject/pb_hooks/`. The exact filename is up to you, but it must end with `.pb.js` so PocketBase picks it up at boot.
- The hook must intercept incoming API requests that create records in the built-in `users` collection.
- Before the record is persisted, the hook must rewrite the submitted `email` value so that it has all leading/trailing whitespace removed AND is fully lowercased.
- Only the `users` collection should be affected. Other auth collections (such as `_superusers`) must NOT have their email modified by this hook.
- The hook must work whether the submitted email is already clean or whether it contains surrounding whitespace and mixed casing.
- Start the PocketBase server bound to all interfaces on TCP port 8090.

## Implementation Hints
- PocketBase v0.31.0 uses the post-v0.23 hook API: handlers must propagate the chain (otherwise the operation is silently blocked).
- The relevant request-level hook gives you access to the in-flight record via the event payload; the record exposes per-field getter/setter helpers.
- Hook files placed under `pb_hooks/` with a `.pb.js` suffix are automatically loaded at server startup. They run inside an embedded JS engine that does NOT support `Promise` / `async / await`; keep the hook strictly synchronous.
- You do NOT need to (re)create the superuser, modify the `users` collection schema, or write any client code - PocketBase ships with a usable `users` collection by default.

## Acceptance Criteria
- Project path: `/home/user/myproject`
- Start command: `./pocketbase serve --http=0.0.0.0:8090`
- Port: 8090
- A hook file with the extension `.pb.js` exists under `/home/user/myproject/pb_hooks/`.
- After the server is running, creating a new user through the public REST API `POST /api/collections/users/records` with a JSON body of the form

  ```json
  {
    "email": "<some email with surrounding whitespace and/or mixed casing>",
    "password": "<password>",
    "passwordConfirm": "<same password>"
  }
  ```

  must return HTTP 200 and the resulting user record (queried after authenticating as that user via `POST /api/collections/users/auth-with-password`) must have its `email` field stored entirely in lowercase with no leading or trailing whitespace.
- Submitting an already clean email must still succeed (no errors and no further modification).
- The hook must NOT affect non-`users` auth collections: a superuser auth login via `POST /api/collections/_superusers/auth-with-password` with the original (mixed-case or whitespace-padded form of the existing) email must still fail, while logging in with the exact stored superuser email succeeds. In other words, the hook does not change behaviour for `_superusers`.

