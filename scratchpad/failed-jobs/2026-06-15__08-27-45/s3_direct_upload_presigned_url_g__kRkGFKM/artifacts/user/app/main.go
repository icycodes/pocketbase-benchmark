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
	"github.com/pocketbase/pocketbase/tools/hook"
)

type presignRequest struct {
	Filename    string `json:"filename"`
	ContentType string `json:"contentType"`
}

type presignResponse struct {
	URL string `json:"url"`
	Key string `json:"key"`
}

func main() {
	app := pocketbase.New()

	app.OnServe().Bind(&hook.Handler[*core.ServeEvent]{
		Id: "presignUpload",
		Func: func(e *core.ServeEvent) error {
			e.Router.POST("/api/presign-upload", func(re *core.RequestEvent) error {
				return presignUploadHandler(re)
			})
			return e.Next()
		},
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}

func presignUploadHandler(re *core.RequestEvent) error {
	var req presignRequest
	if err := re.BindBody(&req); err != nil {
		return re.BadRequestError("invalid request body", nil)
	}

	if req.Filename == "" {
		return re.BadRequestError("filename is required", nil)
	}
	if req.ContentType == "" {
		return re.BadRequestError("contentType is required", nil)
	}

	endpoint := os.Getenv("S3_ENDPOINT")
	region := os.Getenv("S3_REGION")
	bucket := os.Getenv("S3_BUCKET")
	accessKey := os.Getenv("S3_ACCESS_KEY")
	secretKey := os.Getenv("S3_SECRET_KEY")

	if endpoint == "" || region == "" || bucket == "" || accessKey == "" || secretKey == "" {
		return re.InternalServerError("S3 configuration is incomplete; check environment variables", nil)
	}

	// Generate a unique object key preserving the original file extension.
	ext := filepath.Ext(req.Filename)
	key := uuid.New().String() + ext

	cfg, err := config.LoadDefaultConfig(context.Background(),
		config.WithRegion(region),
		config.WithCredentialsProvider(credentials.NewStaticCredentialsProvider(accessKey, secretKey, "")),
	)
	if err != nil {
		log.Printf("failed to load AWS config: %v", err)
		return re.InternalServerError("failed to configure S3 client", nil)
	}

	s3Client := s3.NewFromConfig(cfg, func(o *s3.Options) {
		o.BaseEndpoint = aws.String(endpoint)
		o.UsePathStyle = true
	})

	presignClient := s3.NewPresignClient(s3Client)

	presignedReq, err := presignClient.PresignPutObject(context.Background(), &s3.PutObjectInput{
		Bucket:      aws.String(bucket),
		Key:         aws.String(key),
		ContentType: aws.String(req.ContentType),
	}, func(opts *s3.PresignOptions) {
		opts.Expires = 15 * time.Minute
	})
	if err != nil {
		log.Printf("failed to presign URL: %v", err)
		return re.InternalServerError("failed to generate presigned URL", nil)
	}

	return re.JSON(http.StatusOK, presignResponse{
		URL: presignedReq.URL,
		Key: key,
	})
}
