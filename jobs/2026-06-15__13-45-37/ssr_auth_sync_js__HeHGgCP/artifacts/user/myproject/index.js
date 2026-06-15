const express = require('express');
const cookieParser = require('cookie-parser');
const PocketBase = require('pocketbase').default;

const app = express();
const PORT = 3000;

app.use(cookieParser());

// PocketBase Auth Synchronization Middleware
app.use(async (req, res, next) => {
  // Create a new PocketBase instance per request to avoid state leakage
  const pb = new PocketBase('http://127.0.0.1:8090');
  req.pb = pb;

  // Load the auth store from the request cookie
  const cookieHeader = req.headers.cookie || '';
  pb.authStore.loadFromCookie(cookieHeader);

  try {
    if (pb.authStore.isValid) {
      // Attempt to refresh the auth token
      await pb.collection('users').authRefresh();
    }
  } catch (err) {
    // If refresh fails, clear the auth store
    pb.authStore.clear();
  }

  // Set the pb_auth cookie in response headers
  // We use secure: false since we're testing on localhost / http
  const cookieString = pb.authStore.exportToCookie({ httpOnly: true, secure: false });
  res.setHeader('Set-Cookie', cookieString);

  next();
});

// Protected Profile Route
app.get('/profile', (req, res) => {
  const pb = req.pb;

  if (!pb.authStore.isValid || !pb.authStore.model) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  res.json({
    id: pb.authStore.model.id,
    email: pb.authStore.model.email
  });
});

app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});
