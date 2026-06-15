const express = require("express");
const cookieParser = require("cookie-parser");
const PocketBase = require("pocketbase/cjs");

const app = express();
const PORT = 3000;
const PB_URL = "http://127.0.0.1:8090";

app.use(cookieParser());

/**
 * SSR Authentication Synchronization Middleware
 *
 * For every request:
 *  1. Creates a fresh PocketBase instance to avoid sharing state between requests.
 *  2. Loads the `pb_auth` cookie from the incoming request into the auth store.
 *  3. Attempts to refresh the token via the PocketBase API.
 *  4. Exports the (possibly updated) auth state back to a `Set-Cookie` header so
 *     the client always holds a fresh token.
 *  5. Attaches the PocketBase instance to `res.locals.pb` for use in route handlers.
 */
async function pbAuthMiddleware(req, res, next) {
  const pb = new PocketBase(PB_URL);

  // Load whatever the client sent in the pb_auth cookie (may be empty/absent).
  pb.authStore.loadFromCookie(req.headers["cookie"] || "");

  try {
    // Only attempt a refresh when the store has a (potentially valid) token.
    if (pb.authStore.isValid) {
      await pb.collection("users").authRefresh();
    }
  } catch (_) {
    // Token is expired or invalid — clear the auth store so the cookie that
    // gets exported below reflects the unauthenticated state.
    pb.authStore.clear();
  }

  // Always write back the (refreshed or cleared) cookie so the client stays in
  // sync with the server's auth state.
  res.setHeader(
    "Set-Cookie",
    pb.authStore.exportToCookie({ httpOnly: true, secure: false })
  );

  // Make the PocketBase instance available to downstream route handlers.
  res.locals.pb = pb;

  next();
}

app.use(pbAuthMiddleware);

/**
 * GET /profile
 *
 * Returns the authenticated user's id and email when a valid pb_auth cookie is
 * present, or 401 Unauthorized otherwise.
 */
app.get("/profile", (req, res) => {
  const pb = res.locals.pb;

  if (!pb.authStore.isValid || !pb.authStore.record) {
    return res.status(401).json({ error: "Unauthorized" });
  }

  const { id, email } = pb.authStore.record;
  return res.status(200).json({ id, email });
});

app.listen(PORT, () => {
  console.log(`Server listening on http://localhost:${PORT}`);
});
