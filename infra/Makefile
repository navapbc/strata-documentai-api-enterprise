.PHONY: \
	infra-apply \
	infra-bootstrap \
	infra-deploy \
	infra-destroy \
	infra-format \
	infra-init \
	infra-lint \
	infra-output \
	infra-plan \
	infra-validate \
	help

.DEFAULT_GOAL := help

ENVIRONMENT ?= dev
TF_DIR := environments/$(ENVIRONMENT)
STATE_BUCKET ?= $(shell echo "docai-tfstate-$$(aws sts get-caller-identity $(if $(AWS_PROFILE),--profile $(AWS_PROFILE)) --query Account --output text)-$(ENVIRONMENT)")
AWS_ARGS := $(if $(AWS_PROFILE),--profile $(AWS_PROFILE))

infra-bootstrap: ## Create S3 state bucket for $ENVIRONMENT
	@echo "Creating state bucket: $(STATE_BUCKET)"
	aws s3api create-bucket --bucket $(STATE_BUCKET) --region us-east-1 $(AWS_ARGS)
	aws s3api put-bucket-versioning --bucket $(STATE_BUCKET) --versioning-configuration Status=Enabled $(AWS_ARGS)
	aws s3api put-public-access-block --bucket $(STATE_BUCKET) --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true $(AWS_ARGS)
	@echo "State bucket ready: $(STATE_BUCKET)"
	@echo "Run: make infra-init ENVIRONMENT=$(ENVIRONMENT)"

infra-init: ## Initialize Terraform for $ENVIRONMENT
	terraform -chdir="$(TF_DIR)" init -input=false -reconfigure \
		-backend-config="bucket=$(STATE_BUCKET)" \
		-backend-config="key=docai/$(ENVIRONMENT)/terraform.tfstate" \
		-backend-config="region=us-east-1" \
		-backend-config="use_lockfile=true"

infra-plan: ## Plan infrastructure changes for $ENVIRONMENT
	@IMAGE_TAG=$${IMAGE_TAG:-$$(git -C .. rev-parse --short HEAD)} && \
	terraform -chdir="$(TF_DIR)" plan -var="image_tag=$$IMAGE_TAG"

infra-apply: ## Apply infrastructure changes for $ENVIRONMENT
	@IMAGE_TAG=$${IMAGE_TAG:-$$(git -C .. rev-parse --short HEAD)} && \
	terraform -chdir="$(TF_DIR)" apply -var="image_tag=$$IMAGE_TAG"

infra-deploy: ## Build, push image, and deploy for $ENVIRONMENT
	@echo "Deploying to $(ENVIRONMENT)..."
	@echo "Ensuring ECR repository exists..."
	terraform -chdir="$(TF_DIR)" apply -target=module.ecr -auto-approve
	@ECR_URL=$$(terraform -chdir="$(TF_DIR)" output -raw ecr_repository_url) && \
	IMAGE_TAG=$${IMAGE_TAG:-$$(git -C .. rev-parse --short HEAD)} && \
	REGION=$$(grep 'region' $(TF_DIR)/terraform.tfvars | head -1 | awk -F'"' '{print $$2}') && \
	echo "ECR: $$ECR_URL" && \
	echo "Tag: $$IMAGE_TAG" && \
	echo "Region: $$REGION" && \
	aws ecr get-login-password --region $$REGION $(AWS_ARGS) | docker login --username AWS --password-stdin $$ECR_URL && \
	docker build --platform linux/amd64 -f ../documentai-api/Dockerfile.lambda -t $$ECR_URL:$$IMAGE_TAG ../documentai-api && \
	docker push $$ECR_URL:$$IMAGE_TAG && \
	terraform -chdir="$(TF_DIR)" apply -var="image_tag=$$IMAGE_TAG" -auto-approve && \
	echo "Deploy complete: $$IMAGE_TAG → $(ENVIRONMENT)"

infra-destroy: ## Destroy infrastructure for $ENVIRONMENT
	terraform -chdir="$(TF_DIR)" destroy

infra-output: ## Show Terraform outputs for $ENVIRONMENT
	terraform -chdir="$(TF_DIR)" output

infra-format: ## Format Terraform code
	terraform fmt -recursive .

infra-lint: ## Lint Terraform code (check formatting)
	terraform fmt -recursive -check .

infra-validate: ## Validate Terraform modules
	@for dir in modules/*/; do \
		echo "Validating $$dir"; \
		terraform -chdir="$$dir" init -backend=false > /dev/null 2>&1; \
		terraform -chdir="$$dir" validate; \
	done

help: ## Show help
	@grep -Eh '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "ENVIRONMENT=$(ENVIRONMENT)"
