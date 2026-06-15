# Expand Nested Relations with the PocketBase Dart SDK

## Goal
Write a Dart CLI in `/home/user/myproject` that uses the official `pocketbase` Dart SDK to fetch every comment for a given `posts.id`, expanding the `author` relation and the nested `post.category` relation in a single request against the PocketBase v0.31.0 server, and prints the normalized result as JSON to stdout.

## Acceptance Criteria
- Project path: /home/user/myproject
- Command: `dart run bin/main.dart <postId>`
- The PocketBase base URL is read from the `PB_URL` environment variable (defaults to `http://127.0.0.1:8090`).
- The command must exit with status code `0` for both existing and non-existing post ids.
- For an unknown `<postId>`, stdout must be exactly `[]\n`.
- For a matching `<postId>`, stdout must be a single JSON array (no extra lines, no log noise) where each element strictly matches:

  ```json
  {
    "id": "<comment id>",
    "content": "<comment content>",
    "author": { "id": "<user id>", "email": "<user email>" },
    "post": {
      "id": "<post id>",
      "title": "<post title>",
      "category": { "id": "<category id>", "name": "<category name>" }
    }
  }
  ```

- Elements must be sorted ascending by the comment's `created` timestamp.
- Only the JSON array may be written to stdout; any diagnostics must go to stderr or be suppressed.

