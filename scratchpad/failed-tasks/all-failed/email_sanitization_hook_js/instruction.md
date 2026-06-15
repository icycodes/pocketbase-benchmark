# PocketBase Email Sanitization Hook

## Background
In a PocketBase application, it's important to keep user data consistent. Email addresses should always be stored in lowercase and without leading or trailing spaces to avoid authentication issues or duplicate accounts.

## Requirements
- Create a PocketBase JavaScript event hook that intercepts record creation and updates for the `users` collection.
- Sanitize the `email` field of the record by trimming whitespace from both ends and converting all characters to lowercase.
- The hook must apply these changes before the record is validated and saved to the database.

## Implementation Hints
- Use PocketBase's JSVM hook functions such as `onRecordCreateRequest` and `onRecordUpdateRequest` (available in PocketBase v0.23+).
- Access the record's `email` field, sanitize the string, and use the record setter to update the field.
- Remember to call `e.next()` to continue the request chain.
- Save your script as a `.pb.js` file in the `pb_hooks` directory.

## Acceptance Criteria
- Project path: `/home/user/pocketbase`
- Start command: `./pocketbase serve --http=0.0.0.0:8090`
- Port: `8090`
- API Endpoints:
  - POST `/api/collections/users/records`: Creates a new user. The response must contain the newly created user record with the sanitized email.

    ```json
    // Request
    {
      "email": string,
      "password": string,
      "passwordConfirm": string
    }
    ```

  - PATCH `/api/collections/users/records/:id`: Updates an existing user. The response must contain the updated user record with the sanitized email.

    ```json
    // Request
    {
      "email": string
    }
    ```

