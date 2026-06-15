# S3 Presigned URL Direct Upload Route

## Background
PocketBase proxies file uploads through its own API, which can cause memory spikes and latency for large files when using S3 storage. To bypass this, developers often implement direct-to-bucket uploads via AWS presigned URLs.

## Requirements
- Create a custom Go route `POST /api/presign-upload` in a PocketBase application.
- The route must accept a JSON payload containing `filename` (string) and `contentType` (string).
- It must generate an S3 presigned URL for a `PUT` request to upload the file directly to an S3 bucket.
- The S3 configuration must be read from environment variables: `S3_ENDPOINT`, `S3_REGION`, `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`.
- The generated presigned URL must be valid for 15 minutes.
- The object key should be uniquely generated (e.g., using a UUID or a timestamp prefix) to avoid collisions, preserving the original file extension.
- Return the presigned URL and the generated object key in a JSON response.

## Implementation Hints
- Initialize a custom PocketBase application in Go.
- Register a custom POST route `/api/presign-upload` using the PocketBase router (`app.Router().AddRoute(...)` or `app.OnBeforeServe().Add(...)`).
- Use the official AWS SDK for Go v2 (`github.com/aws/aws-sdk-go-v2`, `config`, `s3`, and `s3/presign`) to configure the S3 client and generate the presigned URL.
- Ensure the S3 client uses the endpoint provided in `S3_ENDPOINT` (with path-style URLs enabled if necessary for compatibility with MinIO/custom endpoints).

## Acceptance Criteria
- Project path: /home/user/app
- Start command: go run main.go serve --http="0.0.0.0:8090"
- Port: 8090
- API Endpoints:
  - POST `/api/presign-upload`: Accepts a JSON payload and returns status 200 with the presigned URL and object key.

    ```json
    // Request
    {
      "filename": "example.png",
      "contentType": "image/png"
    }
    ```
    ```json
    // Response
    {
      "url": "string",
      "key": "string"
    }
    ```
- The returned `url` must be a valid presigned URL that successfully accepts a `PUT` request with the specified file and content type.

