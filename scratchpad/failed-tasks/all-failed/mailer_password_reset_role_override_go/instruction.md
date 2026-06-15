# PocketBase Password Reset Email Override

## Background
You are building a PocketBase backend using Go. You need to customize the password reset email template dynamically based on the user's role.

## Requirements
- Implement a Go hook in `main.go` to intercept the password reset email for the `users` collection.
- The `users` collection has a `role` text field.
- If the user's `role` is `admin`, change the email subject to `Admin Password Reset - {APP_NAME}` and the HTML body to exactly `Admin Reset Link: {ACTION_URL}`.
- If the user's `role` is `user`, change the email subject to `User Password Reset - {APP_NAME}` and the HTML body to exactly `User Reset Link: {ACTION_URL}`.
- Do not modify the email for other roles.

## Implementation Hints
- Use the `OnMailerRecordPasswordResetSend` hook provided by the PocketBase Go SDK.
- You can access the user record from the hook event to check the `role` field.
- You can access `{APP_NAME}` via `$app.settings().meta.appName` (or equivalent Go method: `e.App.Settings().Meta.AppName`).
- You can construct the `{ACTION_URL}` using the token from `e.Meta["token"].(string)` and the base action URL from `e.App.Settings().Meta.ResetPasswordTemplate.ActionUrl`. Wait, actually you can just use the built-in template registry to resolve placeholders, or manually replace `{APP_NAME}` and `{ACTION_URL}`. Actually, PocketBase evaluates placeholders *after* the hook if you modify the raw template, but wait! The hook `OnMailerRecordPasswordResetSend` receives `e.Message` which has already been rendered! So you need to construct the final string yourself, or modify the `e.Message.Subject` and `e.Message.HTML` directly.
- Since `e.Message` is already rendered, you must provide the final string. You can get the app name from `e.App.Settings().Meta.AppName`. You can get the reset token from `e.Meta["token"].(string)`. The default ActionUrl can be retrieved from `e.App.Settings().Meta.ResetPasswordTemplate.ActionUrl`, and you should replace `{TOKEN}` in it with the actual token to form the final ActionUrl.

## Acceptance Criteria
- Project path: /home/user/app
- Start command: go run main.go serve --http 0.0.0.0:8090
- Port: 8090
- API Endpoints:
  - Standard PocketBase password reset endpoint: `POST /api/collections/users/request-password-reset`
- When requesting a password reset for a user with `role="admin"`, the outgoing email must have the subject `Admin Password Reset - <AppName>` and HTML body `Admin Reset Link: <ActionUrl>`.
- When requesting a password reset for a user with `role="user"`, the outgoing email must have the subject `User Password Reset - <AppName>` and HTML body `User Reset Link: <ActionUrl>`.

