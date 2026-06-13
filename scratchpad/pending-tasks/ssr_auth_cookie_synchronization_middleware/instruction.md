Because PocketBase is stateless and defaults to storing JWTs in browser `localStorage`, Server-Side Rendered (SSR) frameworks require custom middleware to synchronize the authentication state via HTTP cookies.

You need to implement a SvelteKit `hooks.server.js` middleware function that synchronizes the PocketBase auth state. The middleware must read the cookie from the incoming request, load it into a server-side PocketBase SDK instance, perform an `authRefresh()` if the user is valid, and write the newly refreshed token back to the response headers.

**Constraints:**
- You MUST use `pb.authStore.loadFromCookie()` to parse the incoming request.
- You MUST use `pb.authStore.exportToCookie()` to update the response headers.
- Do NOT expose the server-side admin credentials; only operate on the user's client-provided cookie state.