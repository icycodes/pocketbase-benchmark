# Relational Access Control Rule in PocketBase

## Background
Configure API rules in PocketBase to enforce relational access control. You need to create collections for `projects` and `tasks`, and restrict access to tasks based on project membership.

## Requirements
- Initialize a PocketBase standalone application.
- Create a `projects` collection with fields: `name` (text) and `members` (relation to `users` collection, multiple).
- Create a `tasks` collection with fields: `title` (text) and `project` (relation to `projects` collection, single).
- Configure the `listRule` and `viewRule` on the `tasks` collection so that users can only list and view tasks if they are assigned to the parent `project` via the `members` relational field.
- The `listRule` and `viewRule` for `projects` can be set to allow members to view them, or left open for testing, but the primary requirement is the `tasks` collection rules.
- Implement this using JS migrations in the `pb_migrations` directory so that it runs automatically when the server starts.

## Implementation Hints
- Download the PocketBase binary (v0.31.0 for linux amd64) and extract it to the project path.
- Create a JS migration file in the `pb_migrations` directory to programmatically create the collections and set the API rules.
- The API rule for relational checks uses dot notation (e.g., `@request.auth.id ?= project.members`).
- Ensure the PocketBase server binds to `0.0.0.0:8090`.

## Acceptance Criteria
- Project path: /home/user/myproject
- Start command: ./pocketbase serve --http="0.0.0.0:8090"
- Port: 8090
- Collections:
  - `projects` collection exists with `name` (text) and `members` (relation to `users`).
  - `tasks` collection exists with `title` (text) and `project` (relation to `projects`).
- API Rules:
  - A user authenticated via the REST API can list and view a task ONLY IF they are in the `members` array of the task's parent project.
  - A user cannot list or view tasks belonging to projects they are not members of.

