package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	awsconfig "github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/credentials"
	"github.com/aws/aws-sdk-go-v2/service/s3"
	"github.com/aws/aws-sdk-go-v2/service/s3/types"
	"github.com/google/uuid"
	"github.com/pocketbase/dbx"
	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/apis"
	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase/tools/hook"
)

const (
	defaultS3Endpoint = "http://127.0.0.1:9000"
	defaultS3AccessKey = "minioadmin"
	defaultS3SecretKey = "minioadmin"
	defaultS3Region    = "us-east-1"
	defaultS3Bucket    = "uploads"
	presignDuration    = 300 * time.Second
)

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func main() {
	app := pocketbase.New()

	app.OnServe().BindFunc(func(e *core.ServeEvent) error {
		// Bootstrap collections and seed users
		if err := bootstrap(e.App); err != nil {
			log.Printf("bootstrap error: %v", err)
		}

		// Register custom routes
		e.Router.POST("/api/uploads/presign", presignHandler(e.App)).
			Bind(apis.RequireAuth("users"))
		e.Router.POST("/api/uploads/finalize", finalizeHandler(e.App)).
			Bind(apis.RequireAuth("users"))

		return e.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}

func bootstrap(app core.App) error {
	// Create collections
	createPendingUploadCollection(app)
	createUploadsCollection(app)
	// Seed users
	seedSuperuser(app)
	seedRegularUser(app, "user@example.com", "password1234")
	seedRegularUser(app, "other@example.com", "password1234")
	return nil
}

func createPendingUploadCollection(app core.App) {
	existing, _ := app.FindCollectionByNameOrId("pending_upload")
	if existing != nil {
		return
	}

	usersCollection, err := app.FindCollectionByNameOrId("users")
	if err != nil {
		log.Printf("users collection not found: %v", err)
		return
	}

	collection := core.NewBaseCollection("pending_upload")
	collection.Fields.Add(&core.RelationField{
		Name:         "user",
		Required:     true,
		CollectionId: usersCollection.Id,
		MaxSelect:    1,
	})
	collection.Fields.Add(&core.TextField{
		Name:     "key",
		Required: true,
		Pattern:  "^[a-f0-9-]{16,}$",
	})
	collection.Fields.Add(&core.DateField{
		Name:     "expires_at",
		Required: true,
	})

	if err := app.Save(collection); err != nil {
		log.Printf("failed to create pending_upload collection: %v", err)
	} else {
		log.Printf("created pending_upload collection")
	}
}

func createUploadsCollection(app core.App) {
	existing, _ := app.FindCollectionByNameOrId("uploads")
	if existing != nil {
		return
	}

	usersCollection, err := app.FindCollectionByNameOrId("users")
	if err != nil {
		log.Printf("users collection not found: %v", err)
		return
	}

	collection := core.NewBaseCollection("uploads")
	collection.Fields.Add(&core.RelationField{
		Name:         "user",
		Required:     true,
		CollectionId: usersCollection.Id,
		MaxSelect:    1,
	})
	collection.Fields.Add(&core.TextField{
		Name:     "key",
		Required: true,
		Pattern:  "^[a-f0-9-]{16,}$",
	})

	if err := app.Save(collection); err != nil {
		log.Printf("failed to create uploads collection: %v", err)
	} else {
		log.Printf("created uploads collection")
	}
}

func seedSuperuser(app core.App) {
	superusers, err := app.FindCollectionByNameOrId(core.CollectionNameSuperusers)
	if err != nil {
		log.Printf("_superusers collection not found: %v", err)
		return
	}

	// Check if admin already exists
	existing, _ := app.FindAuthRecordByEmail(core.CollectionNameSuperusers, "admin@example.com")
	if existing != nil {
		return
	}

	record := core.NewRecord(superusers)
	record.Set("email", "admin@example.com")
	record.Set("password", "1234567890")
	record.Set("passwordConfirm", "1234567890")

	if err := app.Save(record); err != nil {
		log.Printf("failed to seed superuser: %v", err)
	} else {
		log.Printf("seeded superuser admin@example.com")
	}
}

func seedRegularUser(app core.App, email, password string) {
	users, err := app.FindCollectionByNameOrId("users")
	if err != nil {
		log.Printf("users collection not found: %v", err)
		return
	}

	// Check if user already exists
	existing, _ := app.FindAuthRecordByEmail("users", email)
	if existing != nil {
		return
	}

	record := core.NewRecord(users)
	record.Set("email", email)
	record.Set("password", password)
	record.Set("passwordConfirm", password)
	record.Set("name", email)

	if err := app.Save(record); err != nil {
		log.Printf("failed to seed user %s: %v", email, err)
	} else {
		log.Printf("seeded user %s", email)
	}
}

func newS3Client() (*s3.Client, *s3.PresignClient, error) {
	s3Endpoint := getEnv("S3_ENDPOINT", defaultS3Endpoint)
	s3AccessKey := getEnv("S3_ACCESS_KEY", defaultS3AccessKey)
	s3SecretKey := getEnv("S3_SECRET_KEY", defaultS3SecretKey)
	s3Region := getEnv("S3_REGION", defaultS3Region)

	cfg, err := awsconfig.LoadDefaultConfig(context.Background(),
		awsconfig.WithRegion(s3Region),
		awsconfig.WithCredentialsProvider(credentials.NewStaticCredentialsProvider(s3AccessKey, s3SecretKey, "")),
	)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to create S3 config: %w", err)
	}

	client := s3.NewFromConfig(cfg, func(o *s3.Options) {
		o.BaseEndpoint = aws.String(s3Endpoint)
		o.UsePathStyle = true
	})

	presigner := s3.NewPresignClient(client)

	return client, presigner, nil
}

func presignHandler(app core.App) func(e *core.RequestEvent) error {
	return func(e *core.RequestEvent) error {
		authRecord := e.Auth

		key := uuid.New().String()
		expiresAt := time.Now().Add(presignDuration)

		_, presigner, err := newS3Client()
		if err != nil {
			return e.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to create S3 client"})
		}

		s3Bucket := getEnv("S3_BUCKET", defaultS3Bucket)

		presignReq, err := presigner.PresignPutObject(context.Background(), &s3.PutObjectInput{
			Bucket: aws.String(s3Bucket),
			Key:    aws.String(key),
		}, func(opts *s3.PresignOptions) {
			opts.Expires = presignDuration
		})
		if err != nil {
			log.Printf("failed to presign: %v", err)
			return e.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to create presigned URL"})
		}

		// Create pending_upload record
		pendingCollection, err := app.FindCollectionByNameOrId("pending_upload")
		if err != nil {
			return e.JSON(http.StatusInternalServerError, map[string]string{"error": "pending_upload collection not found"})
		}

		pendingRecord := core.NewRecord(pendingCollection)
		pendingRecord.Set("user", authRecord.Id)
		pendingRecord.Set("key", key)
		pendingRecord.Set("expires_at", expiresAt.UTC().Format(time.RFC3339))

		if err := app.Save(pendingRecord); err != nil {
			log.Printf("failed to save pending_upload: %v", err)
			return e.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to create pending_upload record"})
		}

		return e.JSON(http.StatusOK, map[string]any{
			"url":       presignReq.URL,
			"key":       key,
			"expiresAt": expiresAt.UTC().Format(time.RFC3339),
		})
	}
}

func finalizeHandler(app core.App) func(e *core.RequestEvent) error {
	return func(e *core.RequestEvent) error {
		authRecord := e.Auth

		var body struct {
			Key string `json:"key"`
		}
		if err := json.NewDecoder(e.Request.Body).Decode(&body); err != nil || body.Key == "" {
			return e.JSON(http.StatusBadRequest, map[string]string{"error": "invalid request body"})
		}

		// Find the pending_upload record
		pendingCollection, err := app.FindCollectionByNameOrId("pending_upload")
		if err != nil {
			return e.JSON(http.StatusInternalServerError, map[string]string{"error": "pending_upload collection not found"})
		}

		pendingRecord, err := app.FindFirstRecordByFilter(
			pendingCollection.Id,
			"key = {:key}",
			dbx.Params{"key": body.Key},
		)
		if err != nil {
			return e.JSON(http.StatusNotFound, map[string]string{"error": "pending upload not found"})
		}

		// Verify ownership
		if pendingRecord.GetString("user") != authRecord.Id {
			return e.JSON(http.StatusNotFound, map[string]string{"error": "pending upload not found"})
		}

		// Verify object exists in S3 via HEAD request
		s3Client, _, err := newS3Client()
		if err != nil {
			return e.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to create S3 client"})
		}

		s3Bucket := getEnv("S3_BUCKET", defaultS3Bucket)

		_, err = s3Client.HeadObject(context.Background(), &s3.HeadObjectInput{
			Bucket: aws.String(s3Bucket),
			Key:    aws.String(body.Key),
		})
		if err != nil {
			var nfe *types.NotFound
			if errors.As(err, &nfe) {
				return e.JSON(http.StatusNotFound, map[string]string{"error": "object not found in S3"})
			}
			// For MinIO, HEAD object returns a generic error for 404
			log.Printf("HEAD object error: %v", err)
			return e.JSON(http.StatusNotFound, map[string]string{"error": "object not found in S3"})
		}

		// Delete the pending_upload record
		if err := app.Delete(pendingRecord); err != nil {
			return e.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to delete pending_upload record"})
		}

		// Create the uploads record
		uploadsCollection, err := app.FindCollectionByNameOrId("uploads")
		if err != nil {
			return e.JSON(http.StatusInternalServerError, map[string]string{"error": "uploads collection not found"})
		}

		uploadRecord := core.NewRecord(uploadsCollection)
		uploadRecord.Set("user", authRecord.Id)
		uploadRecord.Set("key", body.Key)

		if err := app.Save(uploadRecord); err != nil {
			return e.JSON(http.StatusInternalServerError, map[string]string{"error": "failed to create uploads record"})
		}

		return e.JSON(http.StatusOK, map[string]any{
			"key": body.Key,
		})
	}
}