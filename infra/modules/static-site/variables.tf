variable "name" {
  type        = string
  description = "Name prefix for the static-site resources (S3 bucket, CloudFront distribution)."
}

variable "default_root_object" {
  type        = string
  description = "Object CloudFront serves for requests to the root path."
  default     = "index.html"
}
