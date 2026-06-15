# S3 Presigned URL Generator for Large Files

## Background
When PocketBase is configured with S3 storage, file uploads are proxied through the server. For large files (e.g., >20MB), this buffering can cause memory exhaustion. A robust resolution is to implement direct-to-bucket uploads using S3 presigned URLs, bypassing PocketBase's default file proxy for the upload phase.

## Requirements
- Create a custom Go application embedding PocketBase.
- Implement a custom REST API route `GET /api/s3-presign`.
- The route must accept a query parameter `filename`.
- The route must generate and return an AWS S3 presigned URL for a `PUT` operation, allowing a client to upload a file directly to the S3 bucket.
- The S3 object key must be formatted as `uploads/<run-id>/<filename>`, where `<run-id>` is read from the `ZEALT_RUN_ID` environment variable.
- The application should read S3 configuration from the environment variables: `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `AWS_BUCKET`.

## Implementation Hints
- Initialize a Go module and add PocketBase as a dependency.
- Use `app.OnBeforeServe().BindFunc(...)` to register a new `GET` route `/api/s3-presign` on the PocketBase router.
- Use the AWS SDK for Go (e.g., `github.com/aws/aws-sdk-go` or v2) to configure an S3 client and generate a presigned `PutObject` request.
- Extract the `filename` from the request query parameters. If missing, return a 400 Bad Request error.
- Return the generated URL in a JSON response.

## Acceptance Criteria
- Project path: /home/user/myproject
- Start command: go run main.go serve --http="0.0.0.0:8090"
- Port: 8090
- API Endpoints:
  - GET `/api/s3-presign?filename=<filename>`: Returns status 200 and a JSON object containing the presigned URL.

    ```json
    // Response
    {
      "url": "https://..."
    }
    ```
  - GET `/api/s3-presign`: Returns status 400 if the `filename` query parameter is missing.
- The returned URL must be a valid S3 presigned URL containing the correct bucket name, region, object key (`uploads/<run-id>/<filename>`), and AWS signature parameters.

