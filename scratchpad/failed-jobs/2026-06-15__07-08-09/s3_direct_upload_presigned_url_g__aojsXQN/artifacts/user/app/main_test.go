package main

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"
	"time"
)

func TestPresignUploadRoute(t *testing.T) {
	// 1. Start a mock S3 server
	mockS3 := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// The request should be a PUT to /test-bucket/<key>
		if r.Method != http.MethodPut {
			t.Errorf("expected PUT request, got %s", r.Method)
			w.WriteHeader(http.StatusMethodNotAllowed)
			return
		}

		// Check the bucket in the path (since UsePathStyle is true)
		if !strings.HasPrefix(r.URL.Path, "/test-bucket/") {
			t.Errorf("expected path to start with /test-bucket/, got %s", r.URL.Path)
			w.WriteHeader(http.StatusBadRequest)
			return
		}

		// Check the Content-Type header
		contentType := r.Header.Get("Content-Type")
		if contentType != "image/png" {
			t.Errorf("expected Content-Type image/png, got %s", contentType)
			w.WriteHeader(http.StatusBadRequest)
			return
		}

		// Verify signature query parameters exist
		query := r.URL.Query()
		if query.Get("X-Amz-Signature") == "" {
			t.Errorf("missing S3 signature query parameter")
			w.WriteHeader(http.StatusForbidden)
			return
		}

		w.WriteHeader(http.StatusOK)
	}))
	defer mockS3.Close()

	// 2. Set environment variables
	os.Setenv("S3_ENDPOINT", mockS3.URL)
	os.Setenv("S3_REGION", "us-east-1")
	os.Setenv("S3_BUCKET", "test-bucket")
	os.Setenv("S3_ACCESS_KEY", "test-access-key")
	os.Setenv("S3_SECRET_KEY", "test-secret-key")

	// 3. Start PocketBase server in a goroutine
	os.Args = []string{"main", "serve", "--http=127.0.0.1:8090"}
	
	go func() {
		main()
	}()

	// Wait for server to start
	time.Sleep(1 * time.Second)

	// 4. Send POST request to /api/presign-upload
	payload := map[string]string{
		"filename":    "test-image.png",
		"contentType": "image/png",
	}
	payloadBytes, _ := json.Marshal(payload)

	resp, err := http.Post("http://127.0.0.1:8090/api/presign-upload", "application/json", bytes.NewBuffer(payloadBytes))
	if err != nil {
		t.Fatalf("failed to send request to /api/presign-upload: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		t.Fatalf("expected status 200, got %d. Body: %s", resp.StatusCode, string(body))
	}

	var respData struct {
		URL string `json:"url"`
		Key string `json:"key"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&respData); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}

	if respData.URL == "" {
		t.Errorf("expected non-empty URL in response")
	}
	if respData.Key == "" {
		t.Errorf("expected non-empty Key in response")
	}
	if !strings.HasSuffix(respData.Key, ".png") {
		t.Errorf("expected key to preserve extension .png, got %s", respData.Key)
	}

	// 5. Test PUT request to the generated presigned URL
	req, err := http.NewRequest(http.MethodPut, respData.URL, strings.NewReader("dummy image content"))
	if err != nil {
		t.Fatalf("failed to create PUT request: %v", err)
	}
	req.Header.Set("Content-Type", "image/png")

	putResp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("failed to execute PUT request: %v", err)
	}
	defer putResp.Body.Close()

	if putResp.StatusCode != http.StatusOK {
		t.Errorf("expected PUT status 200, got %d", putResp.StatusCode)
	}
}
