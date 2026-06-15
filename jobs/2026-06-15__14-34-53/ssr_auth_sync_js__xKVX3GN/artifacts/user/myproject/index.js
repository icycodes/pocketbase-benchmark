const express = require('express');
const cookieParser = require('cookie-parser');
const PocketBase = require('pocketbase/cjs');

const app = express();
app.use(cookieParser());

// Middleware to sync PocketBase auth
app.use(async (req, res, next) => {
  // Initialize pocketbase instance
  const pb = new PocketBase('http://127.0.0.1:8090');
  
  // load the auth store state from the request cookie string
  const cookieHeader = req.headers.cookie || '';
  pb.authStore.loadFromCookie(cookieHeader);

  try {
    // get an up-to-date auth store state by verifying and refreshing the loaded model
    if (pb.authStore.isValid) {
      await pb.collection('users').authRefresh();
    }
  } catch (err) {
    // clear the auth store on failed refresh
    pb.authStore.clear();
  }

  // send back the default 'pb_auth' cookie to the client with the latest store state
  res.appendHeader('Set-Cookie', pb.authStore.exportToCookie());
  
  // Make pb available to route handlers
  res.locals.pb = pb;
  
  next();
});

app.get('/profile', (req, res) => {
  const pb = res.locals.pb;
  if (pb.authStore.isValid && pb.authStore.model) {
    res.status(200).json({
      id: pb.authStore.model.id,
      email: pb.authStore.model.email
    });
  } else {
    res.status(401).json({ error: 'Unauthorized' });
  }
});

app.listen(3000, () => {
  console.log('Server started on port 3000');
});
