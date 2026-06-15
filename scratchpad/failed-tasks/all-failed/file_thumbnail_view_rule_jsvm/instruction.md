# PocketBase File Thumbnails with ViewRule and JSVM Whitelist

## Background
Build a PocketBase v0.31.0 photo service that hosts a `photos` collection with image thumbnails, enforces fine-grained file access via a ViewRule, and uses a JSVM hook to strictly restrict which thumb sizes can be served.

## Goal
Configure a PocketBase server that:
- Exposes a `photos` base collection holding images with a small set of predeclared thumbnail sizes.
- Allows file access only to the owner of the photo OR when the photo is marked public.
- Refuses on-the-fly thumb generation for any thumb size that is not predeclared.

## Acceptance Criteria
- Project path: /home/user/myproject
- Start command: `./pocketbase serve --http=0.0.0.0:8090 --dir=/home/user/myproject/pb_data`
- Port: 8090
- The `photos` collection MUST be a `base` collection with at least the following fields:
  - `owner`: relation field to the built-in `users` collection (required).
  - `image`: a single `file` field that accepts standard image MIME types and predeclares the thumbnail sizes `100x100` and `400x300t`.
  - `is_public`: a `bool` field defaulting to `false`.
- The `photos` collection ViewRule MUST be exactly:
  `owner = @request.auth.id || is_public = true`
- File download endpoint `GET /api/files/photos/<recordId>/<filename>` MUST behave as follows:
  - With `?thumb=100x100` or `?thumb=400x300t`:
    - Returns HTTP 200 and a `Content-Type` header that starts with `image/` when the requester is the owner of the record OR when the record's `is_public` is true.
    - Returns HTTP 403 otherwise.
  - With `?thumb=200x200` (or any other thumb size that is not predeclared on the field):
    - Returns HTTP 400 with JSON body exactly `{"message":"unsupported thumb"}` (regardless of authentication state).
  - Without any `thumb` query parameter:
    - Returns HTTP 200 and the original image bytes when the ViewRule passes; returns HTTP 403 otherwise.
- Initial-state setup that MUST be present before the server is started for evaluation:
  - A superuser exists with email `admin@example.com` and password `Admin12345!`.
  - The `users` auth collection allows password authentication.
  - The `photos` collection is created with the schema and ViewRule described above.
  - JSVM hooks are mounted from the `pb_hooks/` directory and contain the unsupported-thumb enforcement.

