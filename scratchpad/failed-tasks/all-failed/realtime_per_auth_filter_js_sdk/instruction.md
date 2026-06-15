# Realtime Per-Auth Filter Test in PocketBase

## Background
PocketBase's Realtime API uses Server-Sent Events (SSE). When subscribing to an entire collection, the collection's `ListRule` is automatically applied to filter which events the subscriber receives based on their authentication state. You need to write a Node.js script using the PocketBase JS SDK to verify this behavior.

## Requirements
- Write a Node.js script (`test_realtime.js`) that connects to a local PocketBase server running at `http://127.0.0.1:8090`.
- The script must programmatically configure the server (using admin credentials) by creating a `messages` collection. The collection must have a `user` field (a relation to the `users` collection) and a `ListRule` set to `user = @request.auth.id`.
- The script must create two distinct users (User A and User B).
- The script must test the realtime subscription by:
  1. Authenticating as User A and subscribing to the `messages` collection.
  2. Creating one message assigned to User A and another message assigned to User B.
  3. Verifying that User A's subscription only receives the SSE event for their own message, and does NOT receive the event for User B's message.
- The script should exit with code 0 and print "Test passed!" on success, or exit with a non-zero code on failure.

## Implementation Hints
- Use the official `pocketbase` npm package.
- You can authenticate as an admin to create collections and users using `pb.admins.authWithPassword()`.
- Remember that realtime subscriptions are asynchronous. You may need to wait briefly (e.g., using `setTimeout` or a sleep function) to ensure all events have been processed before asserting the results.
- Use `pb.collection('messages').subscribe('*', callback)` to listen for events.

## Acceptance Criteria
- Project path: `/home/user/myproject`
- Command: `node test_realtime.js`
- The script must successfully execute from start to finish without manual intervention.
- The stdout should print: `Test passed!`
- The script must exit with status code 0.
- The script must correctly implement the per-auth filter test as described in the requirements (User A only receives their own message events).
