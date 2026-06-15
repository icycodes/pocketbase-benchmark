const express = require("express");
const cookieParser = require("cookie-parser");
const PocketBase = require("pocketbase");

const app = express();
const PORT = 3000;

// Parse cookies so req.cookies is populated
app.use(cookieParser());

// Middleware: synchronize PocketBase auth state via cookies
app.use(async (req, res, next) => {
  const pb = new PocketBase("http://127.0.0.1:8090");

  // Load auth state from the incoming request's cookie header
  pb.authStore.loadFromCookie(req.headers.cookie || "");

  try {
    // Attempt to refresh the authentication state
    if (pb.authStore.isValid) {
      await pb.collection("users").authRefresh();
    }
  } catch (_) {
    // Token is expired or invalid — clear the auth store
    pb.authStore.clear();
  }

  // Export the (possibly refreshed or cleared) auth state to a cookie
  const cookieStr = pb.authStore.exportToCookie();
  res.setHeader("Set-Cookie", cookieStr);

  // Attach the PocketBase instance so route handlers can use it
  req.pb = pb;

  next();
});

// Protected route: /profile
app.get("/profile", (req, res) => {
  const pb = req.pb;

  if (!pb.authStore.isValid) {
    // Ensure the cleared auth state is reflected in the cookie
    const cookieStr = pb.authStore.exportToCookie();
    res.setHeader("Set-Cookie", cookieStr);
    return res.status(401).json({ error: "Unauthorized" });
  }

  const record = pb.authStore.record;
  return res.status(200).json({
    id: record.id,
    email: record.email,
  });
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
