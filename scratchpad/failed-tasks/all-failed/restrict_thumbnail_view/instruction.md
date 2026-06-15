# Restrict File Thumbnail Viewing

## Background
You have a PocketBase project with a `posts` collection. The collection has a file field named `image` with thumbnails enabled. Currently, the file and its thumbnails are publicly accessible.

## Requirements
- Restrict access to the `image` file field (and its thumbnails) so that only authenticated users can view them.
- Use PocketBase's built-in file protection and API rules.
- Ensure unauthenticated requests to the file/thumbnail URL are rejected.
- Ensure authenticated requests (with a valid Auth token or file token) can successfully view the file/thumbnail.

## Implementation Hints
- You will need to modify the collection schema to mark the `image` field as `Protected`.
- You will need to update the `viewRule` of the `posts` collection to require authentication (e.g., `@request.auth.id != ""`).
- Since PocketBase applies the `viewRule` to protected files, this will secure both the original file and its thumbnails.

## Acceptance Criteria
- Project path: /home/user/pb
- Start command: ./pocketbase serve --http=0.0.0.0:8090
- Port: 8090
- Endpoints to check:
  - GET `/api/files/posts/{recordId}/{filename}?thumb=100x100`
- Unauthenticated requests to the thumbnail URL must return a 403 Forbidden (or 401/404 depending on PocketBase's exact error for protected files without auth).
- Authenticated requests (with a valid `Authorization` header from an authenticated user) to the thumbnail URL must return a 200 OK and the file content.
