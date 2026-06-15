# PocketBase View Collection for User Post Counts

## Background
PocketBase supports View Collections, which are read-only collections backed by a custom SQLite query. This allows you to create aggregated views of your data, such as counting the number of related records.

## Requirements
- Initialize a PocketBase application.
- Create a `posts` collection with an `author` relation field pointing to the built-in `users` collection.
- Create a View Collection named `user_post_counts` that joins the `users` and `posts` collections.
- The `user_post_counts` view must return the user's `id`, their `username`, and a `post_count` representing the total number of posts they have authored.
- The schema of the view should include `id` (relation to users or text), `username` (text), and `post_count` (number).

## Implementation Hints
- Use PocketBase's migration system to define the schema for both the `posts` collection and the `user_post_counts` view collection.
- The SQLite query for the view should select from `users`, left join `posts` on the author relation, and group by `users.id`.
- Remember that View Collections require a unique `id` column for each row in the result set.
- You can write a Go migration (`pb_migrations/*.go`) or a JSON migration (`pb_migrations/*.js`) to define the collections programmatically.

## Acceptance Criteria
- Project path: /home/user/myproject
- Start command: ./pocketbase serve --http="0.0.0.0:8090"
- Port: 8090
- Collections:
  - A `posts` collection exists with an `author` field (type: relation, target: `users`).
  - A `user_post_counts` view collection exists.
- API Endpoints:
  - GET `/api/collections/user_post_counts/records`: Returns status 200 and a JSON array of records containing `id`, `username`, and `post_count`.

