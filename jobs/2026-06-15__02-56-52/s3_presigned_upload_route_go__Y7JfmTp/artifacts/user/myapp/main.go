package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/credentials"
	"github.com/aws/aws-sdk-go-v2/service/s3"
	"github.com/google/uuid"
	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
)

func main() {
	app := pocketbase.New()

	app.OnServe().BindFunc(func(e *core.ServeEvent) error {
		// Ensure collections exist
		usersColl, err := e.App.FindCollectionByNameOrId("users")
		if err != nil {
			log.Printf("users collection not found: %v", err)
		} else {
			_, err = e.App.FindCollectionByNameOrId("pending_upload")
			if err != nil {
				coll := core.NewBaseCollection("pending_upload")
				coll.Fields.Add(&core.RelationField{
					Name:         "user",
					Required:     true,
					CollectionId: usersColl.Id,
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
				coll.AddIndex("idx_pending_upload_key", true, "key", "")

				if err := e.App.Save(coll); err != nil {
					log.Printf("failed to save pending_upload: %v", err)
				}
			}

			_, err = e.App.FindCollectionByNameOrId("uploads")
			if err != nil {
				coll := core.NewBaseCollection("uploads")
				coll.Fields.Add(&core.RelationField{
					Name:         "user",
					Required:     true,
					CollectionId: usersColl.Id,
					MaxSelect:    1,
				})
				coll.Fields.Add(&core.TextField{
					Name:     "key",
					Required: true,
				})
				coll.AddIndex("idx_uploads_key", true, "key", "")

				if err := e.App.Save(coll); err != nil {
					log.Printf("failed to save uploads: %v", err)
				}
			}
		}

		// Configure S3 client
		minioHost := os.Getenv("MINIO_HOST")
		if minioHost == "" {
			minioHost = "127.0.0.1:9000"
		}
		minioAccessKey := os.Getenv("MINIO_ACCESS_KEY")
		if minioAccessKey == "" {
			minioAccessKey = "minioadmin"
		}
		minioSecretKey := os.Getenv("MINIO_SECRET_KEY")
		if minioSecretKey == "" {
			minioSecretKey = "minioadmin"
		}
		minioRegion := os.Getenv("MINIO_REGION")
		if minioRegion == "" {
			minioRegion = "us-east-1"
		}
		minioBucket := os.Getenv("MINIO_BUCKET")
		if minioBucket == "" {
			minioBucket = "uploads"
		}

		cfg, err := config.LoadDefaultConfig(context.TODO(),
			config.WithRegion(minioRegion),
			config.WithCredentialsProvider(credentials.NewStaticCredentialsProvider(minioAccessKey, minioSecretKey, "")),
			config.WithEndpointResolverWithOptions(aws.EndpointResolverWithOptionsFunc(func(service, region string, options ...interface{}) (aws.Endpoint, error) {
				return aws.Endpoint{
					URL:               "http://" + minioHost,
					HostnameImmutable: true,
				}, nil
			})),
		)
		if err != nil {
			log.Fatalf("Failed to load AWS config: %v", err)
		}

		s3Client := s3.NewFromConfig(cfg)
		presignClient := s3.NewPresignClient(s3Client, s3.WithPresignExpires(300*time.Second))

		e.Router.POST("/api/uploads/presign", func(req *core.RequestEvent) error {
			if req.Auth == nil || req.Auth.Collection().Name != "users" {
				return req.UnauthorizedError("Unauthorized", nil)
			}

			key := uuid.New().String()
			expiresAt := time.Now().Add(300 * time.Second)

			presignReq, err := presignClient.PresignPutObject(req.Request.Context(), &s3.PutObjectInput{
				Bucket: aws.String(minioBucket),
				Key:    aws.String(key),
			})
			if err != nil {
				return req.InternalServerError("Failed to presign url", err)
			}

			pendingUploadColl, err := req.App.FindCachedCollectionByNameOrId("pending_upload")
			if err != nil {
				return req.InternalServerError("Collection not found", err)
			}

			record := core.NewRecord(pendingUploadColl)
			record.Set("user", req.Auth.Id)
			record.Set("key", key)
			record.Set("expires_at", expiresAt)

			if err := req.App.Save(record); err != nil {
				return req.InternalServerError("Failed to save pending upload", err)
			}

			return req.JSON(http.StatusOK, map[string]any{
				"url":       presignReq.URL,
				"key":       key,
				"expiresAt": expiresAt.Format(time.RFC3339),
			})
		})

		e.Router.POST("/api/uploads/finalize", func(req *core.RequestEvent) error {
			if req.Auth == nil || req.Auth.Collection().Name != "users" {
				return req.UnauthorizedError("Unauthorized", nil)
			}

			var payload struct {
				Key string `json:"key"`
			}
			if err := req.BindBody(&payload); err != nil {
				return req.BadRequestError("Invalid body", err)
			}

			pendingUpload, err := req.App.FindFirstRecordByData("pending_upload", "key", payload.Key)
			if err != nil {
				return req.NotFoundError("Pending upload not found", err)
			}
			if pendingUpload.GetString("user") != req.Auth.Id {
				return req.NotFoundError("Pending upload not found", nil)
			}

			_, err = s3Client.HeadObject(req.Request.Context(), &s3.HeadObjectInput{
				Bucket: aws.String(minioBucket),
				Key:    aws.String(payload.Key),
			})
			if err != nil {
				return req.NotFoundError("Object not found in S3", err)
			}

			err = req.App.RunInTransaction(func(txApp core.App) error {
				if err := txApp.Delete(pendingUpload); err != nil {
					return err
				}

				uploadsColl, err := txApp.FindCachedCollectionByNameOrId("uploads")
				if err != nil {
					return err
				}

				uploadRecord := core.NewRecord(uploadsColl)
				uploadRecord.Set("user", req.Auth.Id)
				uploadRecord.Set("key", payload.Key)

				return txApp.Save(uploadRecord)
			})

			if err != nil {
				return req.InternalServerError("Failed to finalize upload", err)
			}

			return req.JSON(http.StatusOK, map[string]string{
				"key": payload.Key,
			})
		})

		return e.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
