# PocketBase Realtime Subscriptions with Dart SDK

## Background
PocketBase provides a reactive Server-Sent Events (SSE) realtime subscription API. Create a Dart CLI application that uses the PocketBase Dart SDK to subscribe to realtime events, trigger an event by creating a record, and process the received event.

## Requirements
- Initialize a Dart project and add the `pocketbase` package dependency.
- Create a Dart script that connects to a local PocketBase instance.
- Authenticate as a user (credentials will be provided in the environment or setup).
- Subscribe to realtime events on the `posts` collection.
- Create a new record in the `posts` collection. The title of the post must include the `run-id` read from the `ZEALT_RUN_ID` environment variable to ensure isolation.
- Wait to receive the realtime event triggered by the record creation.
- Print the realtime event action and the record title to standard output.
- Exit the script cleanly after receiving the event.

## Implementation Hints
- Read the `ZEALT_RUN_ID` environment variable to construct the post title (e.g., `Realtime Post ${run-id}`).
- Connect to PocketBase at `http://127.0.0.1:8090`.
- Use the `pocketbase` Dart package to authenticate, subscribe to the `posts` collection, and create a record.
- Ensure the script waits for the SSE event to arrive before exiting. You may need to use a Completer or similar mechanism in Dart to wait for the event callback.

## Acceptance Criteria
- Project path: /home/user/dart-realtime
- Command: dart run bin/main.dart
- The command must connect to the local PocketBase instance and authenticate.
- The command must create a new record in the `posts` collection with the title `Realtime Post ${run-id}`.
- The stdout should print the realtime event action and the record title in the format: `Realtime event received: <action> - <title>`.

