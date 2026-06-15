# PocketBase view collection: user_post_stats

## Goal
Configure the PocketBase v0.31.0 application at `/home/user/myproject` so that it exposes a read-only **view collection** named `user_post_stats`. The view must aggregate, for every user in the existing `users` (auth) collection, the total number of `posts` that reference the user as their `author` and the timestamp of that user's most recent post.

## Acceptance Criteria
- Project path: `/home/user/myproject`
- Start command: `go run . serve --http=127.0.0.1:8090`
- Port: `8090`
- A view collection named `user_post_stats` must be present in the running PocketBase instance.
- API endpoint `GET /api/collections/user_post_stats/records?sort=-post_count` must respond with HTTP `200` when called by an authenticated superuser. The JSON response must contain an `items` array.
- Every entry of `items` must include all of the following fields:
    - `id` — a non-empty string that matches the `id` of a record in the built-in `users` collection (one row per user).
    - `user` — the same user id.
    - `email` — the user's email address.
    - `post_count` — an integer `≥ 0` equal to the actual number of `posts` whose `author` field references that user.
    - `last_post_at` — the most recent `posts.created` timestamp (PocketBase RFC3339-style string, e.g. `"2024-11-10 18:45:27.123Z"`) for that user, or an empty string `""` when the user has no posts.
- The endpoint must support PocketBase filtering. In particular, `GET /api/collections/user_post_stats/records?filter=(post_count%3E0)` must return HTTP `200` and only contain users whose `post_count` is strictly greater than zero.
- Sorting by `-post_count` must order results by descending post count.

