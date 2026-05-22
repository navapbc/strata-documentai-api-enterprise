# Dev environment configuration
# Update these values for your AWS account

project_name = "docai"
environment  = "dev"
region       = "us-east-1"
bda_region   = "us-east-1"

create_vpc = true
vpc_name   = ""
image_tag  = "latest"

cpu           = 256
memory        = 512
desired_count = 1

use_lambda_workers = true
use_lambda_api     = true
