terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  default = "us-east-1"
}

variable "bucket_name" {
  default = "csvapp-processed-files"
}

# S3 Bucket for processed CSV files
resource "aws_s3_bucket" "csvapp" {
  bucket = var.bucket_name

  tags = {
    Name        = "csvapp-processed-files"
    Environment = "production"
    ManagedBy   = "terraform"
  }
}

# Block all public access
resource "aws_s3_bucket_public_access_block" "csvapp" {
  bucket = aws_s3_bucket.csvapp.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable versioning
resource "aws_s3_bucket_versioning" "csvapp" {
  bucket = aws_s3_bucket.csvapp.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "csvapp" {
  bucket = aws_s3_bucket.csvapp.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Lifecycle policy — S3 Standard → Glacier transition
resource "aws_s3_bucket_lifecycle_configuration" "csvapp" {
  bucket = aws_s3_bucket.csvapp.id

  rule {
    id     = "glacier-transition"
    status = "Enabled"

    filter {
      prefix = "processed/"
    }

    # Move to Glacier Instant Retrieval after 30 days
    transition {
      days          = 30
      storage_class = "GLACIER_IR"
    }

    # Move to Glacier Deep Archive after 90 days (cheapest)
    transition {
      days          = 90
      storage_class = "DEEP_ARCHIVE"
    }

    # Delete after 1 year
    expiration {
      days = 365
    }
  }
}

output "bucket_name" {
  value = aws_s3_bucket.csvapp.bucket
}

output "bucket_arn" {
  value = aws_s3_bucket.csvapp.arn
}
