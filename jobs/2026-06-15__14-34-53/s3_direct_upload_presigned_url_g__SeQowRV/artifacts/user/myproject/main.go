package main

import (
	"context"
	"fmt"
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
		e.Router.GET("/api/s3-presign", func(reqEvent *core.RequestEvent) error {
			filename := reqEvent.Request.URL.Query().Get("filename")
			if filename == "" {
				return reqEvent.JSON(http.StatusBadRequest, map[string]string{
					"error": "filename query parameter is required",
				})
			}

			runID := os.Getenv("ZEALT_RUN_ID")
			if runID == "" {
				runID = "default"
			}

			region := os.Getenv("AWS_REGION")
			accessKey := os.Getenv("AWS_ACCESS_KEY_ID")
			secretKey := os.Getenv("AWS_SECRET_ACCESS_KEY")
			bucket := os.Getenv("AWS_BUCKET")

			cfg, err := config.LoadDefaultConfig(context.TODO(),
				config.WithRegion(region),
				config.WithCredentialsProvider(credentials.NewStaticCredentialsProvider(accessKey, secretKey, "")),
			)
			if err != nil {
				return reqEvent.JSON(http.StatusInternalServerError, map[string]string{
					"error": "failed to load AWS config",
				})
			}

			client := s3.NewFromConfig(cfg)
			presignClient := s3.NewPresignClient(client)

			key := fmt.Sprintf("uploads/%s/%s", runID, filename)

			presignedReq, err := presignClient.PresignPutObject(context.TODO(), &s3.PutObjectInput{
				Bucket: aws.String(bucket),
				Key:    aws.String(key),
			}, func(po *s3.PresignOptions) {
				po.Expires = 15 * time.Minute
			})

			if err != nil {
				return reqEvent.JSON(http.StatusInternalServerError, map[string]string{
					"error": "failed to generate presigned URL",
				})
			}

			return reqEvent.JSON(http.StatusOK, map[string]string{
				"url": presignedReq.URL,
			})
		})

		return e.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
