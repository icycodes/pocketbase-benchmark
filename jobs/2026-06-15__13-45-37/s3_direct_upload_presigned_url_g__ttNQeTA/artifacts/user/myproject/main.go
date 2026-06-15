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
	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
)

func main() {
	app := pocketbase.New()

	app.OnServe().BindFunc(func(e *core.ServeEvent) error {
		e.Router.GET("/api/s3-presign", func(e *core.RequestEvent) error {
			filename := e.Request.URL.Query().Get("filename")
			if filename == "" {
				return e.BadRequestError("filename query parameter is required", nil)
			}

			awsRegion := os.Getenv("AWS_REGION")
			awsAccessKeyID := os.Getenv("AWS_ACCESS_KEY_ID")
			awsSecretAccessKey := os.Getenv("AWS_SECRET_ACCESS_KEY")
			awsBucket := os.Getenv("AWS_BUCKET")
			zealtRunID := os.Getenv("ZEALT_RUN_ID")

			// Load AWS configuration
			cfg, err := config.LoadDefaultConfig(context.TODO(),
				config.WithRegion(awsRegion),
				config.WithCredentialsProvider(credentials.NewStaticCredentialsProvider(awsAccessKeyID, awsSecretAccessKey, "")),
			)
			if err != nil {
				return e.InternalServerError("Failed to load AWS configuration", err)
			}

			s3Client := s3.NewFromConfig(cfg)
			presignClient := s3.NewPresignClient(s3Client)

			key := "uploads/" + zealtRunID + "/" + filename

			presignedReq, err := presignClient.PresignPutObject(context.TODO(), &s3.PutObjectInput{
				Bucket: aws.String(awsBucket),
				Key:    aws.String(key),
			}, func(opts *s3.PresignOptions) {
				opts.Expires = 15 * time.Minute
			})
			if err != nil {
				return e.InternalServerError("Failed to generate presigned URL", err)
			}

			return e.JSON(http.StatusOK, map[string]string{
				"url": presignedReq.URL,
			})
		})

		return e.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
