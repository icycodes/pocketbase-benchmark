# Programmatically Generate Slug with JSVM Hook

## Background
PocketBase allows extending its functionality using JavaScript (ES5) via an embedded Goja engine. In this task, you will create a JSVM event hook to automatically generate a URL-friendly slug from a post's title before the record is saved to the database.

## Requirements
- Ensure the `posts` collection exists. If it doesn't, create it with a `title` (text) and `slug` (text) field. Make sure the collection allows public create access (or at least allows guests to create records) so it can be tested without authentication.
- Intercept record creation for the `posts` collection using a JSVM hook.
- If the `title` field is missing or empty, reject the request with a `BadRequestError` and the message "Title cannot be empty".
- If a `title` is provided, programmatically generate a slug from it and assign it to the `slug` field of the record.
- Ensure the hook properly propagates execution to the next handler in the chain so the record gets saved.

## Implementation Hints
- Create a JavaScript file inside the `pb_hooks` directory (e.g., `pb_hooks/posts.pb.js`).
- Use the `onRecordBeforeCreateRequest` hook and bind it specifically to the `posts` collection.
- The record data can be accessed and modified via the event object.
- Use PocketBase's built-in `$String.slugify()` method to generate the slug.
- Remember that PocketBase v0.23+ requires calling the next handler in the chain to continue execution.

## Acceptance Criteria
- Project path: /home/user/pocketbase_app
- Start command: ./pocketbase serve --http="0.0.0.0:8090"
- Port: 8090
- API Endpoints:
  - POST `/api/collections/posts/records`: Creates a new post.
    - When providing a valid `title`, the response should be a 200 OK and the returned record object must contain a `slug` field with the slugified version of the title.
    - When providing an empty `title` (or omitting it), the response must be a 400 Bad Request with an error message indicating that the title cannot be empty.
