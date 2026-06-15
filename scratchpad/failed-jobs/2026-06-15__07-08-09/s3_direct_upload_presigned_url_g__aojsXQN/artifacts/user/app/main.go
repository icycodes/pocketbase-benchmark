package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"path/filepath"
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

	app.OnServe().BindFunc(func(se *core.ServeEvent) error {
		se.Router.POST("/api/presign-upload", func(e *core.RequestEvent) error {
			var data struct {
				Filename    string `json:"filename"`
				ContentType string `json:"contentType"`
			}
			if err := e.BindBody(&data); err != nil {
				return e.BadRequestError("Failed to read request data", err)
			}

			if data.Filename == "" {
				return e.BadRequestError("filename is required", nil)
			}
			if data.ContentType == "" {
				return e.BadRequestError("contentType is required", nil)
			}

			endpoint := os.Getenv("S3_ENDPOINT")
			region := os.Getenv("S3_REGION")
			bucket := os.Getenv("S3_BUCKET")
			accessKey := os.Getenv("S3_ACCESS_KEY")
			secretKey := os.Getenv("S3_SECRET_KEY")

			if region == "" || bucket == "" || accessKey == "" || secretKey == "" {
				return e.InternalServerError("Missing required S3 environment variables", nil)
			}

			creds := credentials.NewStaticCredentialsProvider(accessKey, secretKey, "")
			cfg, err := config.LoadDefaultConfig(
				context.TODO(),
				config.WithCredentialsProvider(creds),
				config.WithRegion(region),
			)
			if err != nil {
				return e.InternalServerError("Failed to load AWS config", err)
			}

			s3Client := s3.NewFromConfig(cfg, func(o *s3.Options) {
				if endpoint != "" {
					o.BaseEndpoint = aws.String(endpoint)
					o.UsePathStyle = true
				}
			})

			ext := filepath.Ext(data.Filename)
			key := uuid.New().String() + ext

			presignClient := s3.NewPresignClient(s3Client)
			presignedReq, err := presignClient.PresignPutObject(
				context.TODO(),
				&s3.PutObjectInput{
					Bucket:      aws.String(bucket),
					Key:         aws.String(key),
					ContentType: aws.String(data.ContentType),
				},
				s3.WithPresignExpires(15*time.Minute),
			)
			if err != nil {
				return e.InternalServerError("Failed to generate presigned URL", err)
			}

			return e.JSON(http.StatusOK, map[string]string{
				"url": presignedReq.URL,
				"key": key,
			})
		})

		return se.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
