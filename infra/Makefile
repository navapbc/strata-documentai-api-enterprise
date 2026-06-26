.PHONY: \
	infra-apply \
	infra-bootstrap \
	infra-check \
	infra-deploy \
	infra-destroy \
	infra-drift \
	infra-format \
	infra-init \
	infra-lint \
	infra-output \
	infra-plan \
	infra-manifest \
	infra-setup \
	infra-validate \
	help

.DEFAULT_GOAL := help

ENVIRONMENT ?= dev
PROJECT ?= docai
STAGE ?=
TF_DIR := environments/$(ENVIRONMENT)
STATE_BUCKET ?= $(shell echo "docai-tfstate-$$(aws sts get-caller-identity $(if $(AWS_PROFILE),--profile $(AWS_PROFILE)) --query Account --output text)-$(ENVIRONMENT)")
AWS_ARGS := $(if $(AWS_PROFILE),--profile $(AWS_PROFILE))

define WRITE_CONFIG
	@API=$$(terraform -chdir="$(TF_DIR)" output -raw api_endpoint) && \
	POOL=$$(terraform -chdir="$(TF_DIR)" output -raw cognito_user_pool_id) && \
	CLIENT=$$(terraform -chdir="$(TF_DIR)" output -raw cognito_client_id) && \
	DOMAIN=$$(terraform -chdir="$(TF_DIR)" output -raw cognito_domain 2>/dev/null || echo "") && \
	GOOGLE=$$(terraform -chdir="$(TF_DIR)" output -json cognito_google_enabled 2>/dev/null || echo "false") && \
	for dir in ../ui/admin ../ui/demo; do \
		printf '{\n  "api_endpoint": {"value": "%s"},\n  "cognito_user_pool_id": {"value": "%s"},\n  "cognito_client_id": {"value": "%s"},\n  "cognito_domain": {"value": %s},\n  "cognito_google_enabled": {"value": %s}\n}\n' \
			"$$API" "$$POOL" "$$CLIENT" \
			"$$([ -n "$$DOMAIN" ] && echo '"'$$DOMAIN'"' || echo 'null')" \
			"$$GOOGLE" > "$$dir/config.json"; \
	done
endef

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
	$(WRITE_CONFIG)

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
	$(WRITE_CONFIG)

infra-destroy: ## Destroy infrastructure for $ENVIRONMENT
	terraform -chdir="$(TF_DIR)" destroy

infra-output: ## Show Terraform outputs for $ENVIRONMENT
	terraform -chdir="$(TF_DIR)" output

infra-setup: ## Install Python dependencies (validators + dev tools)
	uv sync --extra dev

infra-format: ## Format Terraform and Python code
	terraform fmt -recursive .
	uv run ruff format validators/

infra-lint: ## Lint Terraform and Python code
	terraform fmt -recursive -check .
	uv run ruff check validators/

infra-validate: ## Validate Terraform modules
	@for dir in modules/*/; do \
		echo "Validating $$dir"; \
		terraform -chdir="$$dir" init -backend=false > /dev/null 2>&1; \
		terraform -chdir="$$dir" validate; \
	done

infra-manifest: infra-expected ## Regenerate manifest.json from tfplan.json (requires TF)
	uv run python -m validators.generate --expected tfplan.json --output manifest.json

infra-check: ## Validate deployed infra against manifest.json (no TF needed)
	uv run python -m validators --env $(ENVIRONMENT) --project $(PROJECT) $(if $(STAGE),--stage $(STAGE)) $(if $(AWS_PROFILE),--profile $(AWS_PROFILE))

infra-drift: ## Alias for infra-check
	uv run python -m validators --env $(ENVIRONMENT) --project $(PROJECT) $(if $(STAGE),--stage $(STAGE)) $(if $(AWS_PROFILE),--profile $(AWS_PROFILE))

infra-expected: ## Generate tfplan.json from Terraform plan (read-only, no remote state)
	@echo "Generating tfplan.json from Terraform modules..."
	@printf 'terraform {\n  backend "local" {\n    path = "/tmp/docai-validate-tfstate"\n  }\n}\n' > $(TF_DIR)/backend_override.tf
	@terraform -chdir="$(TF_DIR)" init -reconfigure -input=false > /dev/null 2>&1
	@IMAGE_TAG=$${IMAGE_TAG:-$$(git -C .. rev-parse --short HEAD)} && \
		terraform -chdir="$(TF_DIR)" plan -refresh=false -var="image_tag=$$IMAGE_TAG" -out=/tmp/docai-validate.tfplan > /dev/null 2>&1
	@terraform -chdir="$(TF_DIR)" show -json /tmp/docai-validate.tfplan > tfplan.json
	@rm -f $(TF_DIR)/backend_override.tf /tmp/docai-validate-tfstate /tmp/docai-validate.tfplan
	@terraform -chdir="$(TF_DIR)" init -reconfigure -input=false \
		-backend-config="bucket=$$(echo docai-tfstate-$$(aws sts get-caller-identity $(AWS_ARGS) --query Account --output text)-$(ENVIRONMENT))" \
		-backend-config="key=docai/$(ENVIRONMENT)/terraform.tfstate" \
		-backend-config="region=us-east-1" \
		-backend-config="use_lockfile=true" > /dev/null 2>&1
	@echo "Generated: tfplan.json ($$(python3 -c "import json; d=json.load(open('tfplan.json')); print(sum(len(m.get('resources',[])) for m in d['planned_values']['root_module'].get('child_modules',[])))" ) resources)"

help: ## Show help
	@grep -Eh '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "ENVIRONMENT=$(ENVIRONMENT)"
