package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/credentials"
	"github.com/aws/aws-sdk-go-v2/service/s3"
	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase/tools/hook"
)

func main() {
	app := pocketbase.New()

	app.OnServe().Bind(&hook.Handler[*core.ServeEvent]{
		Id: "s3PresignRoute",
		Func: func(e *core.ServeEvent) error {
			e.Router.GET("/api/s3-presign", func(re *core.RequestEvent) error {
				filename := re.Request.URL.Query().Get("filename")
				if filename == "" {
					return re.JSON(http.StatusBadRequest, map[string]string{
						"error": "filename query parameter is required",
					})
				}

				runID := os.Getenv("ZEALT_RUN_ID")
				region := os.Getenv("AWS_REGION")
				accessKeyID := os.Getenv("AWS_ACCESS_KEY_ID")
				secretAccessKey := os.Getenv("AWS_SECRET_ACCESS_KEY")
				bucket := os.Getenv("AWS_BUCKET")

				cfg, err := config.LoadDefaultConfig(context.TODO(),
					config.WithRegion(region),
					config.WithCredentialsProvider(credentials.NewStaticCredentialsProvider(
						accessKeyID, secretAccessKey, "",
					)),
				)
				if err != nil {
					return re.JSON(http.StatusInternalServerError, map[string]string{
						"error": fmt.Sprintf("failed to load AWS config: %v", err),
					})
				}

				client := s3.NewFromConfig(cfg)
				presignClient := s3.NewPresignClient(client)

				objectKey := fmt.Sprintf("uploads/%s/%s", runID, filename)

				presignedReq, err := presignClient.PresignPutObject(context.TODO(), &s3.PutObjectInput{
					Bucket: aws.String(bucket),
					Key:    aws.String(objectKey),
				})
				if err != nil {
					return re.JSON(http.StatusInternalServerError, map[string]string{
						"error": fmt.Sprintf("failed to generate presigned URL: %v", err),
					})
				}

				return re.JSON(http.StatusOK, map[string]string{
					"url": presignedReq.URL,
				})
			})

			return e.Next()
		},
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}