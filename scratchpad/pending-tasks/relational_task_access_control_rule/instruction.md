PocketBase API Rules evaluate SQL-like expressions at the database level to enforce access control. Often, permissions are based on relational structures rather than direct ownership.

You need to write an API List/View rule string for a `tasks` collection. Users should only be able to list and view a task if their authenticated user ID is linked to the parent `project` via a relational field (i.e., the user is a member of the project that the task belongs to). 

**Constraints:**
- The output MUST be a valid PocketBase rule expression (e.g., using `@request.auth.id`).
- Do NOT write raw SQL `JOIN` statements; you must use PocketBase's dot-notation relational syntax.
- The rule must strictly block unauthenticated requests (guest access).