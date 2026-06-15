# PocketBase API Rules: Prevent Changing Owner

## Background
PocketBase uses SQL-like API rules to secure collection endpoints. You need to configure an Update API rule for a `posts` collection that ensures only the owner can update the record, and strictly prevents the `owner` field itself from being modified during the update.

## Requirements
- Initialize a PocketBase Go application in `/home/user/myproject`.
- Create a `posts` collection with at least the following fields:
  - `title` (type: text)
  - `owner` (type: relation, targeting the built-in `users` collection)
- Configure the **Update API rule** for the `posts` collection to enforce two conditions:
  1. The user performing the update must be the `owner` of the record.
  2. The `owner` field cannot be modified in the update request.

## Implementation Hints
- You can define the collection and rules using PocketBase's Go migrations (`pb_migrations`).
- In the API rule expression, use `@request.auth.id` to check the current user, and the `:isset` modifier on `@request.body` to ensure a field is not being changed.
- Make sure the application starts a standard PocketBase server on port 8090.

## Acceptance Criteria
- Project path: /home/user/myproject
- Start command: go run main.go serve --http="0.0.0.0:8090"
- Port: 8090
- Endpoints & Behavior:
  - The `posts` collection is accessible via the standard PocketBase REST API.
  - An authenticated user can update the `title` of a post they own.
  - An authenticated user receives a 400 or 403 error if they attempt to update the `owner` field of a post they own.
  - An authenticated user receives a 404 or 403 error if they attempt to update a post they do not own.

