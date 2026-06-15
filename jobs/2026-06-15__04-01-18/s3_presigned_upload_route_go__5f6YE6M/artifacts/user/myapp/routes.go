package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"time"

	"github.com/google/uuid"
	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase/daos"
	"github.com/pocketbase/pocketbase/models"
	"github.com/pocketbase/pocketbase/tools/router"
)

const presignedTTL = 300 * time.Second

func registerRoutes(app *pocketbase.PocketBase, se *core.ServeEvent) {
	group := se.Router.Group("/api/uploads")

	group.POST("/presign", func(e *core.RequestEvent) error {
		return handlePresign(app, e)
	})

	group.POST("/finalize", func(e *core.RequestEvent) error {
		return handleFinalize(app, e)
	})
}

// handlePresign handles POST /api/uploads/presign
func handlePresign(app *pocketbase.PocketBase, e *core.RequestEvent) error {
	// Require authentication
	authRecord := e.Auth
	if authRecord == nil || authRecord.Collection().Name != "users" {
		return e.JSON(http.StatusUnauthorized, map[string]string{
			"error": "authentication required",
		})
	}

	// Generate a UUID-like key
	key := uuid.New().String()

	// Calculate expiry
	now := time.Now().UTC()
	expiresAt := now.Add(presignedTTL)

	// Generate presigned URL
	s3Cfg := getS3Config()
	s3Client, err := newS3Client(s3Cfg)
	if err != nil {
		return e.JSON(http.StatusInternalServerError, map[string]string{
			"error": "failed to create S3 client",
		})
	}

	presignedURL, err := GeneratePresignedPutURL(s3Client, s3Cfg.Bucket, key, presignedTTL)
	if err != nil {
		log.Printf("ERROR: failed to generate presigned URL: %v", err)
		return e.JSON(http.StatusInternalServerError, map[string]string{
			"error": "failed to generate presigned URL",
		})
	}

	// Create pending_upload record
	dao := app.Dao()
	pendingCollection, err := dao.FindCollectionByNameOrId("pending_upload")
	if err != nil {
		log.Printf("ERROR: pending_upload collection not found: %v", err)
		return e.JSON(http.StatusInternalServerError, map[string]string{
			"error": "pending_upload collection not found",
		})
	}

	pendingRecord := models.NewRecord(pendingCollection)
	pendingRecord.Set("user", authRecord.Id)
	pendingRecord.Set("key", key)
	pendingRecord.Set("expires_at", expiresAt)

	if err := dao.SaveRecord(pendingRecord); err != nil {
		log.Printf("ERROR: failed to save pending_upload record: %v", err)
		return e.JSON(http.StatusInternalServerError, map[string]string{
			"error": "failed to save pending upload record",
		})
	}

	return e.JSON(http.StatusOK, map[string]interface{}{
		"url":       presignedURL,
		"key":       key,
		"expiresAt": expiresAt.Format(time.RFC3339),
	})
}

// handleFinalize handles POST /api/uploads/finalize
func handleFinalize(app *pocketbase.PocketBase, e *core.RequestEvent) error {
	// Require authentication
	authRecord := e.Auth
	if authRecord == nil || authRecord.Collection().Name != "users" {
		return e.JSON(http.StatusUnauthorized, map[string]string{
			"error": "authentication required",
		})
	}

	// Parse request body
	type finalizeRequest struct {
		Key string `json:"key"`
	}
	var req finalizeRequest
	if err := json.NewDecoder(e.Request.Body).Decode(&req); err != nil {
		return e.JSON(http.StatusBadRequest, map[string]string{
			"error": "invalid request body",
		})
	}

	if req.Key == "" {
		return e.JSON(http.StatusBadRequest, map[string]string{
			"error": "key is required",
		})
	}

	// Verify the object exists in S3
	s3Cfg := getS3Config()
	exists, err := objectExistsHTTP(s3Cfg.Endpoint, s3Cfg.Bucket, req.Key, s3Cfg.AccessKey, s3Cfg.SecretKey, s3Cfg.Region)
	if err != nil {
		log.Printf("ERROR: S3 HEAD request failed: %v", err)
		return e.JSON(http.StatusInternalServerError, map[string]string{
			"error": "failed to verify object in storage",
		})
	}
	if !exists {
		return e.JSON(http.StatusNotFound, map[string]string{
			"error": "object not found in storage",
		})
	}

	// Look up pending_upload record
	dao := app.Dao()
	pendingRecord, err := dao.FindFirstRecordByData("pending_upload", "key", req.Key)
	if err != nil || pendingRecord == nil {
		return e.JSON(http.StatusNotFound, map[string]string{
			"error": "pending upload not found",
		})
	}

	// Verify ownership
	pendingUserID := pendingRecord.GetString("user")
	if pendingUserID != authRecord.Id {
		return e.JSON(http.StatusNotFound, map[string]string{
			"error": "pending upload not found",
		})
	}

	// Delete the pending_upload record
	if err := dao.DeleteRecord(pendingRecord); err != nil {
		log.Printf("ERROR: failed to delete pending_upload record: %v", err)
		return e.JSON(http.StatusInternalServerError, map[string]string{
			"error": "failed to finalize upload",
		})
	}

	// Create the uploads record
	uploadsCollection, err := dao.FindCollectionByNameOrId("uploads")
	if err != nil {
		log.Printf("ERROR: uploads collection not found: %v", err)
		return e.JSON(http.StatusInternalServerError, map[string]string{
			"error": "uploads collection not found",
		})
	}

	uploadRecord := models.NewRecord(uploadsCollection)
	uploadRecord.Set("user", authRecord.Id)
	uploadRecord.Set("key", req.Key)

	if err := dao.SaveRecord(uploadRecord); err != nil {
		log.Printf("ERROR: failed to save uploads record: %v", err)
		return e.JSON(http.StatusInternalServerError, map[string]string{
			"error": "failed to save upload record",
		})
	}

	return e.JSON(http.StatusOK, map[string]string{
		"key": req.Key,
	})
}

// Ensure unused imports don't cause issues
var _ = router.NewGroup("")
var _ = daos.New(nil)
