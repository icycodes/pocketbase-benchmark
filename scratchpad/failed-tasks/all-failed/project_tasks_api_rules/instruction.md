# PocketBase Project Tasks API Rules

## Background
You are building a project management backend using PocketBase. The database schema has already been set up with `projects` and `tasks` collections, but the API rules for the `tasks` collection are currently insecure (accessible to anyone or no one).

## Requirements
- Update the `tasks` collection to secure the `listRule` and `viewRule`.
- A user should only be able to list and view tasks if they are a member of the project that the task belongs to.
- The `projects` collection has a `members` field which is a multiple-relation to the `users` collection.
- The `tasks` collection has a `project` field which is a single-relation to the `projects` collection.
- You may update the collection by writing a JSON migration in `pb_migrations/` or by writing a JS migration.

## Implementation Hints
- Use PocketBase's relational API rules syntax.
- The rule needs to check if the authenticated user's ID is included in the `members` array of the task's expanded `project` relation.
- You can write a JS migration in `pb_migrations/` to update the collection programmatically, or just replace the schema definition if using a declarative approach.

## Acceptance Criteria
- Project path: /home/user/app
- Start command: ./pocketbase serve --http="0.0.0.0:8090"
- Port: 8090
- API Rules:
  - The `tasks` collection must have `listRule` and `viewRule` configured so that only project members can access the tasks.
- Access Control Outcomes:
  - User A (member of Project X) can read Task 1 (belongs to Project X).
  - User B (not a member of Project X) cannot read Task 1.

