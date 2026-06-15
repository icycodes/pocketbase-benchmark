package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"testing"
	"time"
)

type AuthResponse struct {
	Token  string `json:"token"`
	Record struct {
		ID string `json:"id"`
	} `json:"record"`
}

type RecordResponse struct {
	ID    string `json:"id"`
	Title string `json:"title"`
}

type AuditLogItem struct {
	ID         string         `json:"id"`
	Actor      string         `json:"actor"`
	Action     string         `json:"action"`
	Collection string         `json:"collection"`
	Record     string         `json:"record"`
	At         string         `json:"at"`
	Diff       map[string]any `json:"diff"`
}

type AuditLogListResponse struct {
	Items []AuditLogItem `json:"items"`
}

func TestAuditLogFlow(t *testing.T) {
	// 1. Start the PocketBase app in the background
	cmd := exec.Command("./app", "serve", "--http=127.0.0.1:8090")
	// Redirect output to stdout/stderr for debugging if needed
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	err := cmd.Start()
	if err != nil {
		t.Fatalf("Failed to start app: %v", err)
	}
	defer func() {
		// Ensure the process is killed at the end of the test
		if cmd.Process != nil {
			cmd.Process.Kill()
		}
	}()

	// 2. Wait for the server to be ready
	client := &http.Client{Timeout: 5 * time.Second}
	ready := false
	for i := 0; i < 30; i++ {
		resp, err := client.Get("http://127.0.0.1:8090/api/health")
		if err == nil && resp.StatusCode == http.StatusOK {
			ready = true
			resp.Body.Close()
			break
		}
		if err == nil {
			resp.Body.Close()
		}
		time.Sleep(500 * time.Millisecond)
	}

	if !ready {
		t.Fatalf("Server did not become ready in time")
	}

	// 3. Authenticate as the seed user
	authBody, _ := json.Marshal(map[string]string{
		"identity": "test@example.com",
		"password": "1234567890",
	})
	resp, err := client.Post("http://127.0.0.1:8090/api/collections/users/auth-with-password", "application/json", bytes.NewReader(authBody))
	if err != nil {
		t.Fatalf("Failed to send auth request: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		bodyBytes, _ := io.ReadAll(resp.Body)
		t.Fatalf("Auth failed: status %d, body: %s", resp.StatusCode, string(bodyBytes))
	}

	var authData AuthResponse
	if err := json.NewDecoder(resp.Body).Decode(&authData); err != nil {
		t.Fatalf("Failed to decode auth response: %v", err)
	}

	token := authData.Token
	userID := authData.Record.ID
	t.Logf("Authenticated as user ID: %s", userID)

	// Helper to send authorized requests
	sendReq := func(method, url string, body []byte) (*http.Response, error) {
		var bodyReader io.Reader
		if body != nil {
			bodyReader = bytes.NewReader(body)
		}
		req, err := http.NewRequest(method, url, bodyReader)
		if err != nil {
			return nil, err
		}
		req.Header.Set("Content-Type", "application/json")
		req.Header.Set("Authorization", token)
		return client.Do(req)
	}

	// 4. (Scenario 1) Create a posts record with title="Original Title"
	postBody, _ := json.Marshal(map[string]string{
		"title": "Original Title",
	})
	resp, err = sendReq("POST", "http://127.0.0.1:8090/api/collections/posts/records", postBody)
	if err != nil {
		t.Fatalf("Failed to create post: %v", err)
	}
	if resp.StatusCode != http.StatusOK {
		bodyBytes, _ := io.ReadAll(resp.Body)
		t.Fatalf("Create post failed: status %d, body: %s", resp.StatusCode, string(bodyBytes))
	}
	var createdPost RecordResponse
	json.NewDecoder(resp.Body).Decode(&createdPost)
	postID := createdPost.ID
	resp.Body.Close()
	t.Logf("Created post ID: %s", postID)

	// 5. (Scenario 2) Update that record changing ONLY title to "Updated Title"
	updateBody, _ := json.Marshal(map[string]string{
		"title": "Updated Title",
	})
	resp, err = sendReq("PATCH", fmt.Sprintf("http://127.0.0.1:8090/api/collections/posts/records/%s", postID), updateBody)
	if err != nil {
		t.Fatalf("Failed to update post: %v", err)
	}
	if resp.StatusCode != http.StatusOK {
		bodyBytes, _ := io.ReadAll(resp.Body)
		t.Fatalf("Update post failed: status %d, body: %s", resp.StatusCode, string(bodyBytes))
	}
	resp.Body.Close()
	t.Logf("Updated post ID: %s", postID)

	// 6. (Scenario 3) Delete that record
	resp, err = sendReq("DELETE", fmt.Sprintf("http://127.0.0.1:8090/api/collections/posts/records/%s", postID), nil)
	if err != nil {
		t.Fatalf("Failed to delete post: %v", err)
	}
	if resp.StatusCode != http.StatusNoContent {
		bodyBytes, _ := io.ReadAll(resp.Body)
		t.Fatalf("Delete post failed: status %d, body: %s", resp.StatusCode, string(bodyBytes))
	}
	resp.Body.Close()
	t.Logf("Deleted post ID: %s", postID)

	// Wait a moment for any async db operations to settle (though they are synchronous)
	time.Sleep(500 * time.Millisecond)

	// 7. Verify the audit logs
	// Query the audit_log collection, filter by record = postID, sort by created/at ascending
	auditURL := fmt.Sprintf("http://127.0.0.1:8090/api/collections/audit_log/records?filter=(record='%s')&sort=at", postID)
	resp, err = client.Get(auditURL)
	if err != nil {
		t.Fatalf("Failed to get audit logs: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		bodyBytes, _ := io.ReadAll(resp.Body)
		t.Fatalf("Get audit logs failed: status %d, body: %s", resp.StatusCode, string(bodyBytes))
	}

	var logList AuditLogListResponse
	if err := json.NewDecoder(resp.Body).Decode(&logList); err != nil {
		t.Fatalf("Failed to decode audit logs: %v", err)
	}

	if len(logList.Items) != 3 {
		t.Fatalf("Expected exactly 3 audit log rows for record %s, got %d", postID, len(logList.Items))
	}

	// Row 1: Action = Create
	row1 := logList.Items[0]
	if row1.Action != "create" {
		t.Errorf("Row 1 expected action='create', got '%s'", row1.Action)
	}
	if row1.Collection != "posts" {
		t.Errorf("Row 1 expected collection='posts', got '%s'", row1.Collection)
	}
	if row1.Record != postID {
		t.Errorf("Row 1 expected record='%s', got '%s'", postID, row1.Record)
	}
	if row1.Actor != userID {
		t.Errorf("Row 1 expected actor='%s', got '%s'", userID, row1.Actor)
	}
	if len(row1.Diff) != 0 {
		t.Errorf("Row 1 expected empty diff, got %v", row1.Diff)
	}

	// Row 2: Action = Update
	row2 := logList.Items[1]
	if row2.Action != "update" {
		t.Errorf("Row 2 expected action='update', got '%s'", row2.Action)
	}
	if row2.Collection != "posts" {
		t.Errorf("Row 2 expected collection='posts', got '%s'", row2.Collection)
	}
	if row2.Record != postID {
		t.Errorf("Row 2 expected record='%s', got '%s'", postID, row2.Record)
	}
	if row2.Actor != userID {
		t.Errorf("Row 2 expected actor='%s', got '%s'", userID, row2.Actor)
	}

	// Verify diff shape: {"title":{"old":"Original Title","new":"Updated Title"}}
	titleDiff, exists := row2.Diff["title"]
	if !exists {
		t.Errorf("Row 2 expected 'title' key in diff, got %v", row2.Diff)
	} else {
		titleMap, ok := titleDiff.(map[string]any)
		if !ok {
			t.Errorf("Row 2 expected diff.title to be map, got %T", titleDiff)
		} else {
			if titleMap["old"] != "Original Title" {
				t.Errorf("Row 2 expected diff.title.old='Original Title', got '%v'", titleMap["old"])
			}
			if titleMap["new"] != "Updated Title" {
				t.Errorf("Row 2 expected diff.title.new='Updated Title', got '%v'", titleMap["new"])
			}
			if len(titleMap) != 2 {
				t.Errorf("Row 2 expected diff.title to have exactly 2 keys, got %d", len(titleMap))
			}
		}
	}
	if len(row2.Diff) != 1 {
		t.Errorf("Row 2 expected diff to have exactly 1 key, got %d (keys: %v)", len(row2.Diff), row2.Diff)
	}

	// Row 3: Action = Delete
	row3 := logList.Items[2]
	if row3.Action != "delete" {
		t.Errorf("Row 3 expected action='delete', got '%s'", row3.Action)
	}
	if row3.Collection != "posts" {
		t.Errorf("Row 3 expected collection='posts', got '%s'", row3.Collection)
	}
	if row3.Record != postID {
		t.Errorf("Row 3 expected record='%s', got '%s'", postID, row3.Record)
	}
	if row3.Actor != userID {
		t.Errorf("Row 3 expected actor='%s', got '%s'", userID, row3.Actor)
	}
	if len(row3.Diff) != 0 {
		t.Errorf("Row 3 expected empty diff, got %v", row3.Diff)
	}

	// 8. Verify the count of audit_log rows where collection="audit_log" MUST be 0
	auditSelfURL := "http://127.0.0.1:8090/api/collections/audit_log/records?filter=(collection='audit_log')"
	resp, err = client.Get(auditSelfURL)
	if err != nil {
		t.Fatalf("Failed to check self-auditing: %v", err)
	}
	defer resp.Body.Close()
	var selfLogs AuditLogListResponse
	json.NewDecoder(resp.Body).Decode(&selfLogs)
	if len(selfLogs.Items) != 0 {
		t.Errorf("Expected 0 audit log rows with collection='audit_log', got %d", len(selfLogs.Items))
	}

	t.Log("All audit log flow tests passed successfully!")
}
