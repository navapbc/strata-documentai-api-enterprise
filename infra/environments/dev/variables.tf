variable "project_name" {
  type    = string
  default = "docai"
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "region" {
  type    = string
  default = "us-east-1"
}

variable "bda_region" {
  type    = string
  default = "us-east-1"
}

variable "create_vpc" {
  type        = bool
  description = "Create a new VPC (true) or look up existing by name (false)"
  default     = true
}

variable "vpc_name" {
  type        = string
  description = "Name tag of the VPC to look up (only used when create_vpc = false)"
  default     = ""
}


variable "image_tag" {
  type        = string
  description = "Container image tag to deploy"
  default     = "latest"
}

variable "cpu" {
  type    = number
  default = 256
}

variable "memory" {
  type    = number
  default = 512
}

variable "desired_count" {
  type    = number
  default = 1
}

variable "use_lambda_workers" {
  type        = bool
  description = "Use Lambda (true) or ECS tasks via Step Functions (false) for background jobs"
  default     = true
}

variable "use_lambda_api" {
  type        = bool
  description = "Use API Gateway + Lambda (true) or ECS Fargate + ALB (false) for the API"
  default     = false
}

variable "bda_projects" {
  type = map(object({
    managed_blueprint_arns = list(string)
  }))
  description = "Map of BDA projects by document category, each with its own managed blueprint ARNs"
  default = {
    income = {
      managed_blueprint_arns = [
        "arn:aws:bedrock:us-east-1:aws:blueprint/bedrock-data-automation-public-bank-statement",
        "arn:aws:bedrock:us-east-1:aws:blueprint/bedrock-data-automation-public-form-1040",
        "arn:aws:bedrock:us-east-1:aws:blueprint/bedrock-data-automation-public-form-1099-int",
        "arn:aws:bedrock:us-east-1:aws:blueprint/bedrock-data-automation-public-form-1099-misc",
        "arn:aws:bedrock:us-east-1:aws:blueprint/bedrock-data-automation-public-payslip",
        "arn:aws:bedrock:us-east-1:aws:blueprint/bedrock-data-automation-public-w2-form",
      ]
    }
    expenses = {
      managed_blueprint_arns = [
        "arn:aws:bedrock:us-east-1:aws:blueprint/bedrock-data-automation-public-invoice",
        "arn:aws:bedrock:us-east-1:aws:blueprint/bedrock-data-automation-public-receipt",
      ]
    }
    identity = {
      managed_blueprint_arns = [
        "arn:aws:bedrock:us-east-1:aws:blueprint/bedrock-data-automation-public-us-driver-license",
        "arn:aws:bedrock:us-east-1:aws:blueprint/bedrock-data-automation-public-us-passport",
        "arn:aws:bedrock:us-east-1:aws:blueprint/bedrock-data-automation-public-birth-certificate",
      ]
    }
    employment = {
      managed_blueprint_arns = []
    }
    training = {
      managed_blueprint_arns = []
    }
  }
}
