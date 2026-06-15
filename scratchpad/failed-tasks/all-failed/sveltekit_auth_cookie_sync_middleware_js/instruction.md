# SvelteKit Auth Cookie Sync Middleware

## Background
PocketBase is a single-file backend that provides out-of-the-box user authentication. Since PocketBase is stateless and defaults to storing JWTs in browser `localStorage`, Server-Side Rendered (SSR) frameworks like SvelteKit require middleware to sync auth state via cookies.

## Requirements
- Implement a SvelteKit `hooks.server.js` middleware to synchronize PocketBase authentication state using cookies.
- The middleware must intercept incoming requests and initialize a new PocketBase instance for each request at `event.locals.pb` pointing to `http://127.0.0.1:8090`.
- It must read the `pb_auth` cookie from the incoming request and load it into the PocketBase auth store.
- It must attempt to refresh the authentication state using `authRefresh()` on the `users` collection.
- If the token is invalid or expired, it must clear the auth store.
- After the route handler executes, the middleware must write the updated auth state back to the response headers as a `pb_auth` cookie.

## Implementation Hints
- Use `event.locals` to pass the PocketBase instance to SvelteKit route handlers.
- Read the cookie using `event.cookies.get('pb_auth')` or `pb.authStore.loadFromCookie()`.
- Perform `pb.collection('users').authRefresh()` inside a try-catch block. If it throws, call `pb.authStore.clear()`.
- Before returning the response, use `pb.authStore.exportToCookie()` to update the `pb_auth` cookie in the response headers. Note that `exportToCookie()` returns a raw cookie string, so you can append it to the response's `set-cookie` header.

## Acceptance Criteria
- Project path: /home/user/sveltekit-app
- Start command: npm run dev -- --port 5173
- Port: 5173
- API Endpoints/Routes:
  - GET `/` (or any route): When accessed with a valid `pb_auth` cookie, the server must refresh the token and return a new `pb_auth` cookie in the `set-cookie` response header. If accessed with an invalid or expired `pb_auth` cookie, the server must clear the auth state and return a `set-cookie` header that clears the `pb_auth` cookie (e.g., setting its expiration to the past or empty value).
  - The `event.locals.pb.authStore.isValid` state must be correctly populated for downstream handlers.

