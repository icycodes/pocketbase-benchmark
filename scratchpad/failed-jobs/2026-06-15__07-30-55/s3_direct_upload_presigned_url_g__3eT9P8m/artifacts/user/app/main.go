package main

import (
	"context"
	"encoding/json"
	"fmt"
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

type presignRequest struct {
	Filename    string `json:"filename"`
	ContentType string `json:"contentType"`
}

type presignResponse struct {
	URL string `json:"url"`
	Key string `json:"key"`
}

func buildS3PresignClient() (*s3.PresignClient, error) {
	endpoint := os.Getenv("S3_ENDPOINT")
	region := os.Getenv("S3_REGION")
	accessKey := os.Getenv("S3_ACCESS_KEY")
	secretKey := os.Getenv("S3_SECRET_KEY")

	if region == "" {
		region = "us-east-1"
	}

	customResolver := aws.EndpointResolverWithOptionsFunc(
		func(service, reg string, options ...interface{}) (aws.Endpoint, error) {
			if endpoint != "" {
				return aws.Endpoint{
					URL:               endpoint,
					SigningRegion:     region,
					HostnameImmutable: true,
				}, nil
			}
			return aws.Endpoint{}, &aws.EndpointNotFoundError{}
		},
	)

	cfg, err := config.LoadDefaultConfig(
		context.Background(),
		config.WithRegion(region),
		config.WithCredentialsProvider(
			credentials.NewStaticCredentialsProvider(accessKey, secretKey, ""),
		),
		config.WithEndpointResolverWithOptions(customResolver),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to load AWS config: %w", err)
	}

	s3Client := s3.NewFromConfig(cfg, func(o *s3.Options) {
		o.UsePathStyle = true
	})

	return s3.NewPresignClient(s3Client), nil
}

func handlePresignUpload(e *core.RequestEvent) error {
	var req presignRequest
	if err := json.NewDecoder(e.Request.Body).Decode(&req); err != nil {
		return e.JSON(http.StatusBadRequest, map[string]string{
			"error": "invalid request body: " + err.Error(),
		})
	}

	if req.Filename == "" || req.ContentType == "" {
		return e.JSON(http.StatusBadRequest, map[string]string{
			"error": "filename and contentType are required",
		})
	}

	bucket := os.Getenv("S3_BUCKET")
	if bucket == "" {
		return e.JSON(http.StatusInternalServerError, map[string]string{
			"error": "S3_BUCKET environment variable is not set",
		})
	}

	// Build a unique object key: <uuid><original-extension>
	ext := filepath.Ext(req.Filename)
	objectKey := uuid.New().String() + ext

	presignClient, err := buildS3PresignClient()
	if err != nil {
		return e.JSON(http.StatusInternalServerError, map[string]string{
			"error": "failed to initialise S3 client: " + err.Error(),
		})
	}

	presignResult, err := presignClient.PresignPutObject(
		context.Background(),
		&s3.PutObjectInput{
			Bucket:      aws.String(bucket),
			Key:         aws.String(objectKey),
			ContentType: aws.String(req.ContentType),
		},
		s3.WithPresignExpires(15*time.Minute),
	)
	if err != nil {
		return e.JSON(http.StatusInternalServerError, map[string]string{
			"error": "failed to generate presigned URL: " + err.Error(),
		})
	}

	return e.JSON(http.StatusOK, presignResponse{
		URL: presignResult.URL,
		Key: objectKey,
	})
}

func main() {
	app := pocketbase.New()

	app.OnServe().BindFunc(func(se *core.ServeEvent) error {
		se.Router.POST("/api/presign-upload", handlePresignUpload)
		return se.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
