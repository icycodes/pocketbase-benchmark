# PocketBase Strict Email Sanitization Hook (JSVM)

## Background
Ensure user email addresses are consistently formatted by sanitizing them before they are saved to the PocketBase database. We are using PocketBase as a standalone application with JSVM hooks.

## Requirements
- Write a JSVM event hook that intercepts record creation on the `users` collection.
- The hook must automatically lowercase the `email` field.
- The hook must automatically trim leading and trailing whitespace from the `email` field.
- The hook must allow the record creation to proceed after modification.

## Implementation Hints
- Place the hook script in the `pb_hooks` directory.
- Use PocketBase's JSVM event hooks to intercept the record creation request.
- Read and modify the `email` field on the record object.
- Remember that JSVM hook handlers must propagate execution to continue the middleware chain.

## Acceptance Criteria
- Project path: /home/user/myproject
- Start command: ./pocketbase serve --http="0.0.0.0:8090"
- Port: 8090
- API Endpoints:
  - POST `/api/collections/users/records`: When a new user is created, the `email` field is sanitized (lowercased and whitespace trimmed) before being saved.

