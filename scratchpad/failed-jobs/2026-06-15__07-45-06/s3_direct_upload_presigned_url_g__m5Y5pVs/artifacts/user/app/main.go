package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/credentials"
	"github.com/aws/aws-sdk-go-v2/service/s3"
	"github.com/google/uuid"
	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
)

type PresignRequest struct {
	Filename    string `json:"filename"`
	ContentType string `json:"contentType"`
}

type PresignResponse struct {
	Url string `json:"url"`
	Key string `json:"key"`
}

func main() {
	app := pocketbase.New()

	app.OnServe().BindFunc(func(e *core.ServeEvent) error {
		e.Router.POST("/api/presign-upload", func(e *core.RequestEvent) error {
			var req PresignRequest
			if err := json.NewDecoder(e.Request.Body).Decode(&req); err != nil {
				return e.JSON(http.StatusBadRequest, map[string]string{"error": "Invalid JSON payload"})
			}

			if req.Filename == "" || req.ContentType == "" {
				return e.JSON(http.StatusBadRequest, map[string]string{"error": "filename and contentType are required"})
			}

			// Read S3 config from environment
			endpoint := os.Getenv("S3_ENDPOINT")
			region := os.Getenv("S3_REGION")
			bucket := os.Getenv("S3_BUCKET")
			accessKey := os.Getenv("S3_ACCESS_KEY")
			secretKey := os.Getenv("S3_SECRET_KEY")

			if region == "" {
				region = "us-east-1"
			}

			// Configure AWS SDK
			cfg, err := config.LoadDefaultConfig(context.TODO(),
				config.WithRegion(region),
				config.WithCredentialsProvider(credentials.NewStaticCredentialsProvider(accessKey, secretKey, "")),
			)
			if err != nil {
				return e.JSON(http.StatusInternalServerError, map[string]string{"error": "Failed to configure AWS SDK"})
			}

			s3Client := s3.NewFromConfig(cfg, func(o *s3.Options) {
				if endpoint != "" {
					o.BaseEndpoint = aws.String(endpoint)
					o.UsePathStyle = true
				}
			})

			presignClient := s3.NewPresignClient(s3Client)

			// Generate unique object key
			ext := filepath.Ext(req.Filename)
			if ext == "" {
				parts := strings.Split(req.Filename, ".")
				if len(parts) > 1 {
					ext = "." + parts[len(parts)-1]
				}
			}
			
			key := fmt.Sprintf("%s%s", uuid.NewString(), ext)

			// Generate presigned URL
			presignedReq, err := presignClient.PresignPutObject(context.TODO(), &s3.PutObjectInput{
				Bucket:      aws.String(bucket),
				Key:         aws.String(key),
				ContentType: aws.String(req.ContentType),
			}, func(opts *s3.PresignOptions) {
				opts.Expires = 15 * time.Minute
			})

			if err != nil {
				return e.JSON(http.StatusInternalServerError, map[string]string{"error": "Failed to generate presigned URL"})
			}

			return e.JSON(http.StatusOK, PresignResponse{
				Url: presignedReq.URL,
				Key: key,
			})
		})
		
		return e.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
