# Multi-Tenant Organization Permissions in PocketBase

## Background
PocketBase allows defining powerful SQL-like API rules to control access to records. In a multi-tenant B2B application, users belong to organizations with specific roles, and resources belong to those organizations. You need to configure a PocketBase schema and API rules to enforce these multi-tenant access controls.

## Requirements
- Initialize a standalone PocketBase project.
- Create a JS migration file in `pb_migrations` that creates three collections:
  1. `organizations`: Contains a `name` (text) field.
  2. `organization_members`: Contains `user` (relation to `users` collection), `organization` (relation to `organizations` collection), and `role` (select field with options: `owner`, `editor`, `viewer`).
  3. `documents`: Contains `title` (text), `content` (text), and `organization` (relation to `organizations`).
- Configure the following API rules for the `documents` collection:
  - **List/View**: A user can read a document only if they have an `organization_members` record linking them to the document's organization (regardless of role).
  - **Create**: A user can create a document only if they have an `owner` or `editor` role in the organization they are assigning the document to.
  - **Update**: A user can update a document only if they have an `owner` or `editor` role in the document's organization.
  - **Delete**: A user can delete a document only if they have an `owner` role in the document's organization.

## Implementation Hints
- Download and use the PocketBase v0.31.0 linux-amd64 binary.
- Place your schema creation logic inside a JavaScript migration file in the `pb_migrations` directory. PocketBase will run this migration automatically on startup.
- Use the `@collection.organization_members...` syntax in your API rules to query the membership and role of the requesting user (`@request.auth.id`).
- Ensure you check `@request.body.organization` for creation rules and the existing `organization` field for update/delete rules.

## Acceptance Criteria
- Project path: /home/user/myproject
- Start command: ./pocketbase serve --http="0.0.0.0:8090"
- Port: 8090
- API Endpoints:
  - The PocketBase REST API must be active and the collections (`organizations`, `organization_members`, `documents`) must exist.
  - The API rules on the `documents` collection must correctly enforce the role-based access control described in the requirements.

