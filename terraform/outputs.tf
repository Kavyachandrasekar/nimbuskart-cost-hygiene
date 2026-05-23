output "vpc_id" {
  description = "VPC ID"
  value       = module.network.vpc_id
}

output "public_subnet_1_id" {
  description = "Public subnet 1 ID"
  value       = module.network.public_subnet_1_id
}

output "public_subnet_2_id" {
  description = "Public subnet 2 ID"
  value       = module.network.public_subnet_2_id
}
output "bucket_name" {
  description = "S3 bucket name"
  value       = aws_s3_bucket.app_logs.bucket
}
