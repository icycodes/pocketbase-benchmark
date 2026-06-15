package main

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/credentials"
	"github.com/aws/aws-sdk-go-v2/service/s3"
	"github.com/aws/aws-sdk-go-v2/service/s3/types"
)

type S3Config struct {
	Endpoint  string
	Region    string
	AccessKey string
	SecretKey string
	Bucket    string
}

func getS3Config() S3Config {
	return S3Config{
		Endpoint:  getEnv("S3_ENDPOINT", "http://127.0.0.1:9000"),
		Region:    getEnv("S3_REGION", "us-east-1"),
		AccessKey: getEnv("S3_ACCESS_KEY", "minioadmin"),
		SecretKey: getEnv("S3_SECRET_KEY", "minioadmin"),
		Bucket:    getEnv("S3_BUCKET", "uploads"),
	}
}

func getEnv(key, defaultVal string) string {
	if val := os.Getenv(key); val != "" {
		return val
	}
	return defaultVal
}

func newS3Client(cfg S3Config) (*s3.Client, error) {
	resolver := aws.EndpointResolverWithOptionsFunc(func(service, region string, options ...interface{}) (aws.Endpoint, error) {
		return aws.Endpoint{
			URL:               cfg.Endpoint,
			HostnameImmutable: true,
			SigningRegion:     cfg.Region,
		}, nil
	})

	awsCfg, err := config.LoadDefaultConfig(context.Background(),
		config.WithRegion(cfg.Region),
		config.WithCredentialsProvider(credentials.NewStaticCredentialsProvider(cfg.AccessKey, cfg.SecretKey, "")),
		config.WithEndpointResolverWithOptions(resolver),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to load AWS config: %w", err)
	}

	return s3.NewFromConfig(awsCfg, func(o *s3.Options) {
		o.UsePathStyle = true
	}), nil
}

// GeneratePresignedPutURL generates a presigned PUT URL valid for the given duration.
func GeneratePresignedPutURL(client *s3.Client, bucket, key string, ttl time.Duration) (string, error) {
	presignClient := s3.NewPresignClient(client)

	req, err := presignClient.PresignPutObject(context.Background(), &s3.PutObjectInput{
		Bucket: aws.String(bucket),
		Key:    aws.String(key),
	}, s3.WithPresignExpires(ttl))
	if err != nil {
		return "", fmt.Errorf("failed to presign PUT URL: %w", err)
	}

	return req.URL, nil
}

// HeadObject checks if an object exists in the bucket by key.
func HeadObject(client *s3.Client, bucket, key string) (bool, error) {
	_, err := client.HeadObject(context.Background(), &s3.HeadObjectInput{
		Bucket: aws.String(bucket),
		Key:    aws.String(key),
	})
	if err != nil {
		// Check for 404
		var nsk *types.NotFound
		if _, ok := err.(*types.NotFound); ok {
			return false, nil
		}
		// Also check the error string for "Not Found" / 404 patterns
		var respErr *types.ResponseError
		if _, ok := err.(*types.ResponseError); ok {
			return false, nil
		}
		_ = nsk
		_ = respErr
		// Generic check for not found
		return false, err
	}
	return true, nil
}

// HeadObjectExists returns nil if the object exists, or an error if not.
func HeadObjectExists(client *s3.Client, bucket, key string) error {
	_, err := client.HeadObject(context.Background(), &s3.HeadObjectInput{
		Bucket: aws.String(bucket),
		Key:    aws.String(key),
	})
	return err
}

// EnsureBucket creates the bucket if it doesn't exist.
func EnsureBucket(client *s3.Client, bucket string) error {
	_, err := client.HeadBucket(context.Background(), &s3.HeadBucketInput{
		Bucket: aws.String(bucket),
	})
	if err == nil {
		return nil // bucket exists
	}

	_, err = client.CreateBucket(context.Background(), &s3.CreateBucketInput{
		Bucket: aws.String(bucket),
	})
	if err != nil {
		return fmt.Errorf("failed to create bucket %q: %w", bucket, err)
	}
	return nil
}

// Use a simple HTTP HEAD to check object existence (avoids AWS SDK complexity with MinIO)
func objectExistsHTTP(endpoint, bucket, key, accessKey, secretKey, region string) (bool, error) {
	// Build the URL
	url := fmt.Sprintf("%s/%s/%s", endpoint, bucket, key)

	client := &http.Client{Timeout: 10 * time.Second}
	req, err := http.NewRequest("HEAD", url, nil)
	if err != nil {
		return false, err
	}

	resp, err := client.Do(req)
	if err != nil {
		return false, err
	}
	defer resp.Body.Close()

	return resp.StatusCode == http.StatusOK, nil
}
