const express = require('express');
const cookieParser = require('cookie-parser');
const PocketBase = require('pocketbase').default || require('pocketbase');

const PB_URL = 'http://127.0.0.1:8090';

const app = express();
app.use(cookieParser());

// SSR Authentication Synchronization Middleware
// Synchronizes PocketBase auth state between client and server via cookies
app.use(async (req, res, next) => {
  const pb = new PocketBase(PB_URL);

  // Load the pb_auth cookie into the PocketBase auth store
  // loadFromCookie expects the raw cookie header string, not a parsed value
  const cookieHeader = req.headers.cookie || '';
  if (cookieHeader) {
    pb.authStore.loadFromCookie(cookieHeader);
  }

  // If the store appears valid, attempt to refresh the token
  if (pb.authStore.isValid) {
    try {
      await pb.collection('users').authRefresh();
    } catch (_err) {
      // Token is expired or invalid — clear the auth store
      pb.authStore.clear();
    }
  }

  // Export the (possibly refreshed or cleared) auth state to a cookie
  const updatedCookie = pb.authStore.exportToCookie({
    httpOnly: true,
    secure: false,
    sameSite: 'Strict',
    path: '/',
  });

  // Attach the cookie to the response headers
  res.setHeader('Set-Cookie', updatedCookie);

  // Attach the pb instance and auth state to the request for downstream handlers
  req.pb = pb;

  next();
});

// Protected route: returns the authenticated user's id and email
app.get('/profile', (req, res) => {
  const pb = req.pb;

  if (!pb.authStore.isValid || !pb.authStore.record) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  const { id, email } = pb.authStore.record;
  return res.status(200).json({ id, email });
});

const PORT = 3000;
app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
