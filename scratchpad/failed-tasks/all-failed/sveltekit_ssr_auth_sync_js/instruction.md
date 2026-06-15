# SvelteKit SSR Cookie Auth Sync with PocketBase

## Background
You are building a SvelteKit application that uses PocketBase as its backend. To support Server-Side Rendering (SSR) with authenticated users, you need to synchronize the PocketBase authentication state with SvelteKit's server-side request/response flow using cookies.

## Requirements
- Implement a SvelteKit server hook (`src/hooks.server.js`) to synchronize the PocketBase auth store with request cookies.
- The middleware should initialize a new PocketBase instance for each request pointing to `http://127.0.0.1:8090`.
- It must load the auth state from the request cookie, verify/refresh it if valid, and clear it if the refresh fails.
- The PocketBase instance must be attached to `event.locals.pb`.
- After resolving the event, it must serialize the updated auth store state back to the response `set-cookie` header.
- Implement a `POST /api/login` endpoint that reads `email` and `password` from the JSON body, authenticates with PocketBase via `locals.pb.collection('users').authWithPassword()`, and returns a 200 JSON response.
- Implement a `GET /api/me` endpoint that returns 401 Unauthorized if the user is not authenticated, and 200 OK with `{"email": "<user_email>"}` if authenticated (checking `locals.pb.authStore.isValid` and `locals.pb.authStore.model.email`).

## Implementation Hints
- Follow the official PocketBase JS SDK documentation for SSR integration with SvelteKit.
- Use `pb.authStore.loadFromCookie()` to load the initial state from the request headers.
- Use `event.locals.pb.collection('users').authRefresh()` to ensure the token is still valid.
- Use `pb.authStore.exportToCookie()` to send the updated state back to the client.
- Ensure you handle `authRefresh()` failures by clearing the auth store.

## Acceptance Criteria
- Project path: /home/user/sveltekit-app
- Start command: npm run dev
- Port: 5173
- API Endpoints:
  - `POST /api/login`: Accepts JSON `{"email": "...", "password": "..."}` and returns 200 OK. The response headers must include a `set-cookie` header containing `pb_auth`.
  - `GET /api/me`: Returns 401 Unauthorized if no valid `pb_auth` cookie is provided. Returns 200 OK with `{"email": "..."}` if a valid `pb_auth` cookie is provided.

