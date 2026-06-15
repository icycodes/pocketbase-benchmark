# Expand Nested Relations with Dart SDK

## Background
PocketBase supports expanding relational fields in queries so that the full nested record data is returned instead of just the relation ID. You need to write a Dart script that fetches a record and expands its relations up to 3 levels deep.

## Requirements
- Create a Dart script using the official PocketBase Dart SDK.
- The script should connect to a local PocketBase instance (`http://127.0.0.1:8090`).
- Fetch a single record from the `root` collection by its ID (passed as the first command-line argument).
- Expand the nested relations `l1.l2.l3` (level 1 -> level 2 -> level 3).
- Print the fetched record's JSON representation to stdout.

## Implementation Hints
- Use the PocketBase Dart SDK (`pocketbase` package).
- Use `pb.collection('root').getOne(id, expand: 'l1.l2.l3')` to fetch and expand the record.
- Print the JSON representation of the record model to stdout.

## Acceptance Criteria
- Project path: /home/user/myproject
- Command: dart run main.dart <record_id>
- The script must connect to `http://127.0.0.1:8090` without authentication (assuming public read access).
- The stdout should print the JSON representation of the fetched record.
- The printed JSON must include the deeply nested `expand` data up to `l3`.
