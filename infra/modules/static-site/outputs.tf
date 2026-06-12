output "bucket_name" {
  description = "Name of the S3 bucket holding the static site content."
  value       = aws_s3_bucket.site.bucket
}

output "distribution_id" {
  description = "ID of the CloudFront distribution."
  value       = aws_cloudfront_distribution.site.id
}

output "distribution_domain" {
  description = "CloudFront distribution domain name."
  value       = aws_cloudfront_distribution.site.domain_name
}

output "url" {
  description = "Full HTTPS URL of the static site."
  value       = "https://${aws_cloudfront_distribution.site.domain_name}"
}
