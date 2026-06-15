package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	awsconfig "github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/credentials"
	"github.com/aws/aws-sdk-go-v2/service/s3"
	"github.com/google/uuid"
	"github.com/pocketbase/dbx"
	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/apis"
	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase/tools/types"
)

// ---------------------------------------------------------------------------
// S3 helpers
// ---------------------------------------------------------------------------

func getEnv(key, defaultVal string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return defaultVal
}

func s3Params() (endpoint, bucket, region, accessKey, secretKey string) {
	endpoint = getEnv("S3_ENDPOINT", "http://127.0.0.1:9000")
	bucket = getEnv("S3_BUCKET", "uploads")
	region = getEnv("S3_REGION", "us-east-1")
	accessKey = getEnv("S3_ACCESS_KEY", "minioadmin")
	secretKey = getEnv("S3_SECRET_KEY", "minioadmin")
	return
}

func buildAWSConfig() (aws.Config, string, error) {
	endpoint, bucket, region, accessKey, secretKey := s3Params()

	//nolint:staticcheck
	customResolver := aws.EndpointResolverWithOptionsFunc(
		func(service, reg string, options ...interface{}) (aws.Endpoint, error) {
			return aws.Endpoint{
				URL:               endpoint,
				SigningRegion:      region,
				HostnameImmutable: true,
			}, nil
		},
	)

	cfg, err := awsconfig.LoadDefaultConfig(context.Background(),
		awsconfig.WithRegion(region),
		awsconfig.WithEndpointResolverWithOptions(customResolver), //nolint:staticcheck
		awsconfig.WithCredentialsProvider(
			credentials.NewStaticCredentialsProvider(accessKey, secretKey, ""),
		),
	)
	return cfg, bucket, err
}

func newS3Client() (*s3.Client, string, error) {
	cfg, bucket, err := buildAWSConfig()
	if err != nil {
		return nil, bucket, fmt.Errorf("failed to build AWS config: %w", err)
	}
	client := s3.NewFromConfig(cfg, func(o *s3.Options) {
		o.UsePathStyle = true
	})
	return client, bucket, nil
}

func newPresignClient() (*s3.PresignClient, string, error) {
	client, bucket, err := newS3Client()
	if err != nil {
		return nil, bucket, err
	}
	return s3.NewPresignClient(client), bucket, nil
}

// ---------------------------------------------------------------------------
// Collection bootstrap
// ---------------------------------------------------------------------------

func bootstrapCollections(app core.App) error {
	usersColl, err := app.FindCollectionByNameOrId("users")
	if err != nil {
		return fmt.Errorf("cannot find users collection: %w", err)
	}

	// --- pending_upload ---
	if _, err := app.FindCollectionByNameOrId("pending_upload"); err != nil {
		coll := core.NewBaseCollection("pending_upload")

		coll.Fields.Add(&core.RelationField{
			Name:         "user",
			CollectionId: usersColl.Id,
			Required:     true,
			MaxSelect:    1,
		})
		coll.Fields.Add(&core.TextField{
			Name:     "key",
			Required: true,
		})
		coll.Fields.Add(&core.DateField{
			Name:     "expires_at",
			Required: true,
		})

		coll.AddIndex("idx_pending_upload_key_unique", true, "key", "")

		if err := app.Save(coll); err != nil {
			return fmt.Errorf("failed to create pending_upload collection: %w", err)
		}
		log.Println("[bootstrap] Created pending_upload collection")
	} else {
		log.Println("[bootstrap] pending_upload collection already exists")
	}

	// --- uploads ---
	if _, err := app.FindCollectionByNameOrId("uploads"); err != nil {
		coll := core.NewBaseCollection("uploads")

		coll.Fields.Add(&core.RelationField{
			Name:         "user",
			CollectionId: usersColl.Id,
			Required:     true,
			MaxSelect:    1,
		})
		coll.Fields.Add(&core.TextField{
			Name:     "key",
			Required: true,
		})

		coll.AddIndex("idx_uploads_key_unique", true, "key", "")

		if err := app.Save(coll); err != nil {
			return fmt.Errorf("failed to create uploads collection: %w", err)
		}
		log.Println("[bootstrap] Created uploads collection")
	} else {
		log.Println("[bootstrap] uploads collection already exists")
	}

	return nil
}

// ---------------------------------------------------------------------------
// Seeding
// ---------------------------------------------------------------------------

func seedSuperuser(app core.App) error {
	email := "admin@example.com"
	password := "1234567890"

	if existing, err := app.FindAuthRecordByEmail(core.CollectionNameSuperusers, email); err == nil && existing != nil {
		log.Printf("[seed] superuser %s already exists", email)
		return nil
	}

	coll, err := app.FindCollectionByNameOrId(core.CollectionNameSuperusers)
	if err != nil {
		return fmt.Errorf("cannot find superusers collection: %w", err)
	}

	record := core.NewRecord(coll)
	record.Set("email", email)
	record.SetPassword(password)
	if err := app.Save(record); err != nil {
		return fmt.Errorf("failed to save superuser: %w", err)
	}
	log.Printf("[seed] Created superuser %s", email)
	return nil
}

func seedUsers(app core.App) error {
	type seedUser struct{ email, password string }
	users := []seedUser{
		{"user@example.com", "password1234"},
		{"other@example.com", "password1234"},
	}

	usersColl, err := app.FindCollectionByNameOrId("users")
	if err != nil {
		return fmt.Errorf("cannot find users collection: %w", err)
	}

	for _, u := range users {
		if existing, err := app.FindAuthRecordByEmail(usersColl.Id, u.email); err == nil && existing != nil {
			log.Printf("[seed] user %s already exists", u.email)
			continue
		}
		record := core.NewRecord(usersColl)
		record.Set("email", u.email)
		record.Set("emailVisibility", true)
		record.Set("verified", true)
		record.SetPassword(u.password)
		if err := app.Save(record); err != nil {
			return fmt.Errorf("failed to save user %s: %w", u.email, err)
		}
		log.Printf("[seed] Created user %s", u.email)
	}
	return nil
}

// ---------------------------------------------------------------------------
// Handlers
// ---------------------------------------------------------------------------

// presignHandler mints a presigned S3 PUT URL and records a pending_upload.
func presignHandler(e *core.RequestEvent) error {
	// e.Auth is guaranteed non-nil by the RequireAuth("users") middleware
	user := e.Auth

	key := uuid.New().String()

	presignClient, bucket, err := newPresignClient()
	if err != nil {
		return e.InternalServerError("failed to create S3 client", err)
	}

	const presignTTL = 300 * time.Second

	req, err := presignClient.PresignPutObject(context.Background(), &s3.PutObjectInput{
		Bucket: aws.String(bucket),
		Key:    aws.String(key),
	}, s3.WithPresignExpires(presignTTL))
	if err != nil {
		return e.InternalServerError("failed to presign S3 PUT", err)
	}

	expiresAt := time.Now().UTC().Add(presignTTL)
	expiresAtRFC := expiresAt.Format(time.RFC3339)

	// Persist pending_upload record
	pendingColl, err := e.App.FindCollectionByNameOrId("pending_upload")
	if err != nil {
		return e.InternalServerError("cannot find pending_upload collection", err)
	}

	dt, _ := types.ParseDateTime(expiresAt)

	pendingRecord := core.NewRecord(pendingColl)
	pendingRecord.Set("user", user.Id)
	pendingRecord.Set("key", key)
	pendingRecord.Set("expires_at", dt)

	if err := e.App.Save(pendingRecord); err != nil {
		return e.InternalServerError("failed to save pending_upload", err)
	}

	return e.JSON(http.StatusOK, map[string]string{
		"url":       req.URL,
		"key":       key,
		"expiresAt": expiresAtRFC,
	})
}

// finalizeHandler verifies the S3 object exists, deletes the pending record, and creates an upload record.
func finalizeHandler(e *core.RequestEvent) error {
	user := e.Auth

	var body struct {
		Key string `json:"key"`
	}
	if err := e.BindBody(&body); err != nil || body.Key == "" {
		return e.BadRequestError("invalid request body — 'key' is required", nil)
	}

	// Look up pending_upload record by key
	pendingColl, err := e.App.FindCollectionByNameOrId("pending_upload")
	if err != nil {
		return e.InternalServerError("cannot find pending_upload collection", err)
	}

	records, err := e.App.FindRecordsByFilter(
		pendingColl.Id,
		"key = {:key}",
		"",
		1,
		0,
		dbx.Params{"key": body.Key},
	)
	if err != nil || len(records) == 0 {
		return e.NotFoundError("pending upload not found", nil)
	}

	pendingRecord := records[0]

	// Ownership check
	if pendingRecord.GetString("user") != user.Id {
		return e.NotFoundError("pending upload not found", nil)
	}

	// Verify object exists in S3
	s3Client, bucket, err := newS3Client()
	if err != nil {
		return e.InternalServerError("failed to create S3 client", err)
	}

	_, headErr := s3Client.HeadObject(context.Background(), &s3.HeadObjectInput{
		Bucket: aws.String(bucket),
		Key:    aws.String(body.Key),
	})
	if headErr != nil {
		return e.NotFoundError("object not found in S3", nil)
	}

	// Delete pending_upload record
	if err := e.App.Delete(pendingRecord); err != nil {
		return e.InternalServerError("failed to delete pending_upload", err)
	}

	// Create uploads record
	uploadsColl, err := e.App.FindCollectionByNameOrId("uploads")
	if err != nil {
		return e.InternalServerError("cannot find uploads collection", err)
	}

	uploadRecord := core.NewRecord(uploadsColl)
	uploadRecord.Set("user", user.Id)
	uploadRecord.Set("key", body.Key)

	if err := e.App.Save(uploadRecord); err != nil {
		return e.InternalServerError("failed to save upload record", err)
	}

	return e.JSON(http.StatusOK, map[string]string{
		"key": body.Key,
	})
}

// ---------------------------------------------------------------------------
// main
// ---------------------------------------------------------------------------

func main() {
	app := pocketbase.New()

	app.OnServe().BindFunc(func(se *core.ServeEvent) error {
		if err := bootstrapCollections(se.App); err != nil {
			return fmt.Errorf("bootstrapCollections: %w", err)
		}
		if err := seedSuperuser(se.App); err != nil {
			return fmt.Errorf("seedSuperuser: %w", err)
		}
		if err := seedUsers(se.App); err != nil {
			return fmt.Errorf("seedUsers: %w", err)
		}

		// Register API routes under /api/uploads/...
		// RequireAuth("users") ensures only valid "users" collection tokens are accepted.
		uploadsGroup := se.Router.Group("/api/uploads")
		uploadsGroup.Bind(apis.RequireAuth("users"))
		uploadsGroup.POST("/presign", presignHandler)
		uploadsGroup.POST("/finalize", finalizeHandler)

		return se.Next()
	})

	// keep json import referenced
	_ = json.Marshal

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
