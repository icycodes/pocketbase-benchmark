package main

import (
	"context"
	"database/sql"
	"errors"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/credentials"
	"github.com/aws/aws-sdk-go-v2/service/s3"
	"github.com/aws/aws-sdk-go-v2/service/s3/types"
	"github.com/aws/smithy-go"
	"github.com/google/uuid"
	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/apis"
	"github.com/pocketbase/pocketbase/core"
	pbTypes "github.com/pocketbase/pocketbase/tools/types"
)

func main() {
	app := pocketbase.New()

	// S3 Configuration
	endpoint := os.Getenv("S3_ENDPOINT")
	if endpoint == "" {
		endpoint = "http://127.0.0.1:9000"
	}
	accessKey := os.Getenv("AWS_ACCESS_KEY_ID")
	if accessKey == "" {
		accessKey = "minioadmin"
	}
	secretKey := os.Getenv("AWS_SECRET_ACCESS_KEY")
	if secretKey == "" {
		secretKey = "minioadmin"
	}
	region := os.Getenv("AWS_REGION")
	if region == "" {
		region = "us-east-1"
	}
	bucket := os.Getenv("S3_BUCKET")
	if bucket == "" {
		bucket = "uploads"
	}

	// Initialize S3 Client
	cfg, err := config.LoadDefaultConfig(context.Background(),
		config.WithRegion(region),
		config.WithCredentialsProvider(credentials.NewStaticCredentialsProvider(accessKey, secretKey, "")),
	)
	if err != nil {
		log.Fatalf("Failed to load AWS config: %v", err)
	}

	s3Client := s3.NewFromConfig(cfg, func(o *s3.Options) {
		o.BaseEndpoint = aws.String(endpoint)
		o.UsePathStyle = true
	})
	presignClient := s3.NewPresignClient(s3Client)

	// Bind Serve Hook
	app.OnServe().BindFunc(func(e *core.ServeEvent) error {
		// 1. Ensure Collections Exist
		usersCol, err := e.App.FindCollectionByNameOrId("users")
		if err != nil {
			return err
		}

		// Check and create pending_upload collection
		pendingUploadCol, err := e.App.FindCollectionByNameOrId("pending_upload")
		if err != nil {
			if errors.Is(err, sql.ErrNoRows) {
				pendingUploadCol = core.NewBaseCollection("pending_upload")
				pendingUploadCol.Fields.Add(
					&core.RelationField{
						Name:         "user",
						CollectionId: usersCol.Id,
						Required:     true,
						MaxSelect:    1,
					},
					&core.TextField{
						Name:     "key",
						Required: true,
					},
					&core.DateField{
						Name:     "expires_at",
						Required: true,
					},
				)
				pendingUploadCol.AddIndex("idx_pending_upload_key", true, "key", "")
				if err := e.App.Save(pendingUploadCol); err != nil {
					return err
				}
			} else {
				return err
			}
		}

		// Check and create uploads collection
		uploadsCol, err := e.App.FindCollectionByNameOrId("uploads")
		if err != nil {
			if errors.Is(err, sql.ErrNoRows) {
				uploadsCol = core.NewBaseCollection("uploads")
				uploadsCol.Fields.Add(
					&core.RelationField{
						Name:         "user",
						CollectionId: usersCol.Id,
						Required:     true,
						MaxSelect:    1,
					},
					&core.TextField{
						Name:     "key",
						Required: true,
					},
				)
				uploadsCol.AddIndex("idx_uploads_key", true, "key", "")
				if err := e.App.Save(uploadsCol); err != nil {
					return err
				}
			} else {
				return err
			}
		}

		// 2. Register Custom REST Endpoints
		// POST /api/uploads/presign
		e.Router.POST("/api/uploads/presign", func(r *core.RequestEvent) error {
			if r.Auth == nil || r.Auth.Collection().Name != "users" {
				return r.UnauthorizedError("Unauthorized", nil)
			}

			// Generate a server-generated object key (UUID)
			key := uuid.New().String()

			// Calculate expiration time (exactly 300 seconds)
			expiresDuration := 300 * time.Second
			expiresAt := pbTypes.NowDateTime().Add(expiresDuration)
			expiresAtStr := expiresAt.Time().Format(time.RFC3339)

			// Generate S3 PUT presigned URL
			presignedReq, err := presignClient.PresignPutObject(r.Request.Context(), &s3.PutObjectInput{
				Bucket: aws.String(bucket),
				Key:    aws.String(key),
			}, func(o *s3.PresignOptions) {
				o.Expires = expiresDuration
			})
			if err != nil {
				return r.InternalServerError("Failed to generate presigned URL", err)
			}

			// Create a pending_upload record
			pendingRecord := core.NewRecord(pendingUploadCol)
			pendingRecord.Set("user", r.Auth.Id)
			pendingRecord.Set("key", key)
			pendingRecord.Set("expires_at", expiresAt)

			if err := e.App.Save(pendingRecord); err != nil {
				return r.InternalServerError("Failed to save pending upload record", err)
			}

			// Respond with success
			return r.JSON(http.StatusOK, map[string]any{
				"url":       presignedReq.URL,
				"key":       key,
				"expiresAt": expiresAtStr,
			})
		}).Bind(apis.RequireAuth("users"))

		// POST /api/uploads/finalize
		e.Router.POST("/api/uploads/finalize", func(r *core.RequestEvent) error {
			if r.Auth == nil || r.Auth.Collection().Name != "users" {
				return r.UnauthorizedError("Unauthorized", nil)
			}

			// Parse JSON request body
			type FinalizeReq struct {
				Key string `json:"key"`
			}
			var reqBody FinalizeReq
			if err := r.BindBody(&reqBody); err != nil {
				return r.BadRequestError("Invalid request body", err)
			}
			if reqBody.Key == "" {
				return r.BadRequestError("Key is required", nil)
			}

			// Retrieve the pending_upload record for the given key
			pendingRecord, err := e.App.FindFirstRecordByData("pending_upload", "key", reqBody.Key)
			if err != nil {
				if errors.Is(err, sql.ErrNoRows) {
					return r.NotFoundError("Pending upload not found", nil)
				}
				return r.InternalServerError("Failed to query pending upload record", err)
			}

			// Verify it belongs to the authenticated user
			if pendingRecord.GetString("user") != r.Auth.Id {
				return r.NotFoundError("Pending upload not found", nil)
			}

			// Verify object exists in bucket via S3 HEAD request
			_, err = s3Client.HeadObject(r.Request.Context(), &s3.HeadObjectInput{
				Bucket: aws.String(bucket),
				Key:    aws.String(reqBody.Key),
			})
			if err != nil {
				var nsk *types.NoSuchKey
				var nf *types.NotFound
				var apiErr smithy.APIError
				isNotFound := false
				if errors.As(err, &nsk) || errors.As(err, &nf) {
					isNotFound = true
				} else if errors.As(err, &apiErr) {
					code := apiErr.ErrorCode()
					if code == "NotFound" || code == "NoSuchKey" {
						isNotFound = true
					}
				}
				if isNotFound {
					return r.NotFoundError("Object does not exist in S3", nil)
				}
				// Log and return 404 on any other S3 error as required by "If the object does not exist, respond with HTTP 404"
				log.Printf("S3 HEAD error for key %s: %v", reqBody.Key, err)
				return r.NotFoundError("Object does not exist in S3", nil)
			}

			// Transaction: Delete pending_upload record and create uploads record
			err = e.App.RunInTransaction(func(txApp core.App) error {
				if err := txApp.Delete(pendingRecord); err != nil {
					return err
				}

				uploadRecord := core.NewRecord(uploadsCol)
				uploadRecord.Set("user", r.Auth.Id)
				uploadRecord.Set("key", reqBody.Key)

				return txApp.Save(uploadRecord)
			})
			if err != nil {
				return r.InternalServerError("Failed to finalize upload record", err)
			}

			// Respond with success
			return r.JSON(http.StatusOK, map[string]any{
				"key": reqBody.Key,
			})
		}).Bind(apis.RequireAuth("users"))

		return e.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
