package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	awsconfig "github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/credentials"
	"github.com/aws/aws-sdk-go-v2/service/s3"
	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/apis"
	"github.com/pocketbase/pocketbase/core"
)

func main() {
	app := pocketbase.New()

	// Register the /api/s3-presign route before the server starts serving.
	app.OnServe().BindFunc(func(e *core.ServeEvent) error {
		e.Router.GET("/api/s3-presign", func(e *core.RequestEvent) error {
			filename := e.Request.URL.Query().Get("filename")
			if filename == "" {
				return apis.NewBadRequestError("missing required query parameter: filename", nil)
			}

			// Read S3 configuration from environment variables.
			region := os.Getenv("AWS_REGION")
			accessKeyID := os.Getenv("AWS_ACCESS_KEY_ID")
			secretAccessKey := os.Getenv("AWS_SECRET_ACCESS_KEY")
			bucket := os.Getenv("AWS_BUCKET")
			runID := os.Getenv("ZEALT_RUN_ID")

			// Build the S3 object key: uploads/<run-id>/<filename>.
			objectKey := fmt.Sprintf("uploads/%s/%s", runID, filename)

			// Configure the AWS SDK v2 client with static credentials.
			cfg, err := awsconfig.LoadDefaultConfig(
				context.Background(),
				awsconfig.WithRegion(region),
				awsconfig.WithCredentialsProvider(
					credentials.NewStaticCredentialsProvider(accessKeyID, secretAccessKey, ""),
				),
			)
			if err != nil {
				return apis.NewInternalServerError("failed to configure AWS client", err)
			}

			s3Client := s3.NewFromConfig(cfg)
			presignClient := s3.NewPresignClient(s3Client)

			// Generate a presigned PUT URL valid for 15 minutes.
			presignResult, err := presignClient.PresignPutObject(
				context.Background(),
				&s3.PutObjectInput{
					Bucket: aws.String(bucket),
					Key:    aws.String(objectKey),
				},
				s3.WithPresignExpires(15*time.Minute),
			)
			if err != nil {
				return apis.NewInternalServerError("failed to generate presigned URL", err)
			}

			return e.JSON(http.StatusOK, map[string]string{
				"url": presignResult.URL,
			})
		})

		return e.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
