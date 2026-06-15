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

	app.OnServe().BindFunc(func(e *core.ServeEvent) error {
		e.Router.POST("/api/presign-upload", presignUploadHandler)
		return e.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}

func presignUploadHandler(e *core.RequestEvent) error {
	var body struct {
		Filename    string `json:"filename"`
		ContentType string `json:"contentType"`
	}

	if err := e.BindBody(&body); err != nil {
		return e.JSON(http.StatusBadRequest, map[string]string{
			"error": "invalid request body",
		})
	}

	if body.Filename == "" || body.ContentType == "" {
		return e.JSON(http.StatusBadRequest, map[string]string{
			"error": "filename and contentType are required",
		})
	}

	// Read S3 configuration from environment variables
	endpoint := os.Getenv("S3_ENDPOINT")
	region := os.Getenv("S3_REGION")
	bucket := os.Getenv("S3_BUCKET")
	accessKey := os.Getenv("S3_ACCESS_KEY")
	secretKey := os.Getenv("S3_SECRET_KEY")

	// Generate a unique object key preserving the original file extension
	ext := filepath.Ext(body.Filename)
	objectKey := uuid.New().String() + ext

	// Create AWS SDK config with static credentials
	ctx := context.Background()
	cfg, err := config.LoadDefaultConfig(ctx,
		config.WithRegion(region),
		config.WithCredentialsProvider(credentials.NewStaticCredentialsProvider(accessKey, secretKey, "")),
	)
	if err != nil {
		return e.JSON(http.StatusInternalServerError, map[string]string{
			"error": "failed to create AWS config",
		})
	}

	// Create S3 client with custom endpoint and path-style addressing
	client := s3.NewFromConfig(cfg, func(o *s3.Options) {
		if endpoint != "" {
			o.BaseEndpoint = aws.String(endpoint)
		}
		o.UsePathStyle = true
	})

	// Create presign client and generate a presigned PUT URL valid for 15 minutes
	presigner := s3.NewPresignClient(client)

	presignedReq, err := presigner.PresignPutObject(ctx, &s3.PutObjectInput{
		Bucket:      aws.String(bucket),
		Key:         aws.String(objectKey),
		ContentType: aws.String(body.ContentType),
	}, func(opts *s3.PresignOptions) {
		opts.Expires = 15 * time.Minute
	})
	if err != nil {
		return e.JSON(http.StatusInternalServerError, map[string]string{
			"error": "failed to generate presigned URL",
		})
	}

	return e.JSON(http.StatusOK, map[string]string{
		"url": presignedReq.URL,
		"key": objectKey,
	})
}