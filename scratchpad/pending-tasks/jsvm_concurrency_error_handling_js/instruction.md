# JSVM Concurrency Error Handling

## Background
PocketBase supports extending its functionality using an embedded ES5 JavaScript engine (Goja). However, because Goja runs synchronously, asynchronous operations like `Promise`, `async/await`, or non-blocking `fetch` are not supported and will crash the server or cause unexpected behavior. You need to write a synchronous JSVM hook that calls an external webhook and handles errors properly.

## Requirements
- Create a JSVM hook inside `pb_hooks/main.pb.js` that intercepts record creation for the `users` collection.
- The hook must make an HTTP POST request to an external webhook URL provided by the `WEBHOOK_URL` environment variable.
- The JSON payload sent to the webhook must contain the user's email: `{"email": "<user_email>"}`.
- The HTTP request must be synchronous. Do NOT use `Promise` or `async/await`.
- If the webhook responds with a 200 status code, allow the record creation to proceed.
- If the webhook responds with a non-200 status code, the hook must throw a `BadRequestError` with the message "Webhook failed", aborting the record creation.

## Implementation Hints
- The JSVM environment does not support `fetch` with Promises. Use the global `$http.send()` helper to perform synchronous HTTP requests.
- Use `$os.getenv("WEBHOOK_URL")` to read the environment variable.
- Remember to propagate the hook execution chain properly if the request succeeds (e.g., returning `e.next()`).
- You can throw a `BadRequestError` to stop the execution and return a 400 error to the client.

## Acceptance Criteria
- Project path: `/home/user/pocketbase_app`
- Start command: `WEBHOOK_URL=http://127.0.0.1:8081/webhook ./pocketbase serve --http="0.0.0.0:8090"`
- Port: 8090
- API Endpoints:
  - POST `/api/collections/users/records`:
    - When the webhook URL returns 200, the API returns a 200 OK and the user is created.
    - When the webhook URL returns a non-200 status, the API returns a 400 Bad Request with the message "Webhook failed" and the user is NOT created.

