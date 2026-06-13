In complex SaaS applications, data access is heavily regulated by multi-tenant organization roles. A user might have different privilege levels across different organizations.

You need to design exactly two PocketBase API rule strings (one for `ViewRule` and one for `UpdateRule`) for a `documents` collection. The rules must ensure that a user can only view a document if they are a "member" of the parent organization, but can only edit (update) the document if they specifically hold the "editor" role inside that specific organization.

**Constraints:**
- The output MUST consist of exactly two valid, separate PocketBase rule expressions.
- You MUST handle the relational expansion correctly assuming a schema where users belong to an `org_members` collection linking user IDs, org IDs, and roles.
- You MUST ensure the rule verifies the exact role (e.g., `"editor"`) against the authenticated user (`@request.auth.id`).