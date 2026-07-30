# Dev environment configuration
# Update these values for your AWS account

project_name = "docai"
environment  = "dev"
region       = "us-east-1"
bda_region   = "us-east-1"

image_tag = "latest"

# CORS origins are derived automatically from the admin/demo CloudFront
# distributions (see local.cors_allowed_origins in main.tf). These extras cover
# local UI dev servers (admin :3000, demo :3001) hitting the deployed dev API.
# Origins must be full scheme://host:port - bare "localhost" won't match.
extra_cors_allowed_origins = [
  "http://localhost:3000",
  "http://localhost:3001",
  "http://127.0.0.1:3000",
  "http://127.0.0.1:3001",
]
