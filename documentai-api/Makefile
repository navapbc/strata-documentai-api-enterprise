.PHONY: \
	.env.e2e \
	_require-jq \
	api-key \
	api-key-deactivate \
	api-key-list \
	diagrams \
	generate-categories \
	tenant \
	tenant-deactivate \
	tenant-list \
	build \
	check \
	check-blueprint-schemas \
	clean \
	clean-volumes \
	env-from-aws \
	format \
	help \
	init \
	init-local \
	lint \
	lint-mypy \
	lint-ruff \
	lint-uv \
	login \
	openapi-spec \
	postman \
	pull-blueprint-fields \
	pull-blueprint-schemas \
	release-build \
	run-logs \
	setup-env \
	start \
	start-local \
	stop \
	test \
	test-e2e \
	test-e2e-routing \
	test-integration \
	metrics-agg \
	metrics-agg-last-n-days \
	usage-report \

.DEFAULT_GOAL := help

# Check that given variables are set and all have non-empty values,
# die with an error otherwise.
#
# Params:
#   1. Variable name(s) to test.
#   2. (optional) Error message to print.
# Based off of https://stackoverflow.com/questions/10858261/how-to-abort-makefile-if-variable-not-set
check_defined = \
	$(strip $(foreach 1,$1, \
        $(call __check_defined,$1,$(strip $(value 2)))))
__check_defined = \
	$(if $(value $1),, \
		$(error Undefined $1$(if $2, ($2))$(if $(value @), \
			required by target '$@')))

_require-jq:
	@command -v jq >/dev/null || (echo "jq required" && exit 1)

define get_api_lambda_env_vars
	FN=$$(aws lambda list-functions --query "Functions[?contains(FunctionName, 'docai') && ends_with(FunctionName, '-api')].FunctionName" --output text); \
	test -n "$$FN" || (echo "No deployed docai *-api Lambda found" && exit 1); \
	aws lambda get-function-configuration --function-name "$$FN" \
	  --query "Environment.Variables" --output json | \
	jq -r 'to_entries[] | "\(.key)=\(.value)"'
endef

define get_worker_lambda_env_vars
	FN=$$(aws lambda list-functions --query "Functions[?contains(FunctionName, 'docai') && ends_with(FunctionName, '-document-processor')].FunctionName" --output text); \
	test -n "$$FN" || (echo "No deployed docai *-document-processor Lambda found" && exit 1); \
	aws lambda get-function-configuration --function-name "$$FN" \
	  --query "Environment.Variables" --output json | \
	jq -r 'to_entries[] | "\(.key)=\(.value)"'
endef

##################################################
# Constants
##################################################

APP_NAME := documentai-api
APP_DOCS_DIR := $(CURDIR)/../docs/$(APP_NAME)
POSTMAN_DIR := /docs/documentai-api/postman
TF_DIR := ../infra/environments/dev

DIAGRAMS := \
	$(APP_DOCS_DIR)/media/architecture.svg \
	$(APP_DOCS_DIR)/media/request-lifecycle.svg

# By default, all python/uv commands will run inside of the docker container
# if you wish to run this natively, add RUN_CMD_APPROACH=local to your environment vars
# You can set this by either running `export RUN_CMD_APPROACH=local` in your shell or add
# it to your ~/.zshrc file (and run `source ~/.zshrc`)
ifeq "$(RUN_CMD_APPROACH)" "local"
RUN_CMD :=
else
RUN_CMD := docker compose run $(DOCKER_EXEC_ARGS) --rm $(APP_NAME)
endif

PY_RUN_CMD := $(RUN_CMD) uv run --frozen
AWS_RUN_CMD := uv run --frozen

ifdef CI
FMT_ARGS := --check
LINT_ARGS :=
else
FMT_ARGS :=
LINT_ARGS := --fix
endif

##################################################
# Build & Run
##################################################
setup-env: ## Set up local environment file
	@test -f .env || cp local.env.example .env

build: ## Build Docker containers
	docker compose build

start: ## Start containers in detached mode
	docker compose up --renew-anon-volumes --detach

start-local: ## Run the application server natively
	$(PY_RUN_CMD) documentai_api

run-logs: start ## Start containers and follow logs
	docker compose logs --follow --no-color $(APP_NAME)

init: setup-env ## Initialize project (container-based)
	docker compose build

init-local: setup-env ## Initialize project for native development
	uv sync --all-extras --frozen

clean-volumes: ## Remove project docker volumes
	docker compose down --volumes

stop: ## Stop containers
	docker compose down

check: ## Run all checks
check: format lint test test-audit

release-build: ## Build production Docker image
	docker buildx build \
		--platform=linux/amd64 \
		$(OPTS) \
		.

##################################################
# Testing
##################################################

test: ## Run test suite
	$(PY_RUN_CMD) pytest $(args)

test-coverage: ## Run tests with coverage report
	$(PY_RUN_CMD) pytest --cov=src/documentai_api --cov-branch --cov-report=html:.coverage_report --cov-report=term-missing $(args)

test-parallel: ## Run test suite in parallel
	$(PY_RUN_CMD) pytest -n auto $(args)

test-audit: ## Run audit logging tests
	$(PY_RUN_CMD) pytest -m "audit" $(args)

test-integration: ## Run integration tests
	$(PY_RUN_CMD) pytest -m "integration" $(args)

test-e2e: .env.e2e
test-e2e: ## Run e2e tests
	@set -a && . ./.env.e2e && set +a && uv run --frozen pytest tests/e2e -m "e2e and not e2e_routing" -n 4 $(args)

test-e2e-routing: .env.e2e
test-e2e-routing: ## Run e2e routing tests
	@set -a && . ./.env.e2e && set +a && uv run --frozen pytest tests/e2e -m e2e_routing $(args)

.env.e2e: _require-jq ## Generate .env.e2e from deployed Lambda env vars + API Gateway endpoint
# BASE_URL/AWS_REGION aren't in the Lambda's own env (that's API Gateway infra
# metadata, and the Lambda uses BDA_REGION, not AWS_REGION) - e2e tests need
# both by these exact names (tests/e2e/conftest.py, test_app_documents.py),
# so pull them from terraform output rather than the Lambda env dump.
	@{ \
	  echo "# Auto-generated by 'make .env.e2e' - do not edit by hand"; \
	  echo "BASE_URL=$$(terraform -chdir=$(TF_DIR) output -raw api_endpoint)"; \
	  echo "AWS_REGION=$$(terraform -chdir=$(TF_DIR) output -raw region)"; \
	  $(get_worker_lambda_env_vars); \
	  $(get_api_lambda_env_vars); \
	} > .env.e2e
	@chmod 600 .env.e2e
	@echo "Wrote .env.e2e"

# Resource identifiers a locally-run instance of the API needs to reach real
# dev AWS resources - excludes API_AUTH_ENABLED and the Cognito/SSM/CORS vars
# the deployed Lambda has, since those would flip auth away from the
# API_AUTH_INSECURE_SHARED_KEY (local-dev-key) bypass local dev relies on.
ENV_FROM_AWS_KEEP := ^(BDA_PROJECT_ARN_ALL\
|BDA_PROJECT_ARN_PREFIX\
|BDA_PROJECT_ID_[A-Z_]+\
|BDA_PROFILE_ARN\
|BDA_REGION\
|TENANTS_TABLE_NAME\
|DOCUMENTAI_DOCUMENT_METADATA_TABLE_NAME\
|DOCUMENTAI_DOCUMENT_METADATA_JOB_ID_INDEX_NAME\
|DOCUMENTAI_INPUT_LOCATION\
|DOCUMENTAI_OUTPUT_LOCATION\
|DOCUMENTAI_PREPROCESSING_LOCATION)=

# Backslash-continued lines join with a space, (e.g. "BDA_PROJECT_ARN_ALL |BDA_PROFILE_ARN |..."),;
# this breaks the regex above. Remove blank space to create in the desired regex:
# ^(BDA_PROJECT_ARN_ALL|BDA_PROFILE_ARN|...)=
ENV_FROM_AWS_KEEP := $(shell echo '$(ENV_FROM_AWS_KEEP)' | tr -d ' ')

env-from-aws: _require-jq ## Append real dev AWS resource identifiers to .env for live local document processing
# Local docker-compose has no EventBridge/Lambda of its own, but the deployed
# dev environment's S3 -> EventBridge -> Document Processor pipeline reacts to
# any object landing in the real input bucket, regardless of who uploaded it.
# So a document posted to the local API *does* get fully processed, as long as
# .env points at real dev resources instead of the documentai-*-local placeholders.
	@test -f .env || (echo ".env not found - run 'make setup-env' first" && exit 1)
	@$(get_api_lambda_env_vars) | grep -E "$(ENV_FROM_AWS_KEEP)" >> .env
	@tail -r .env | awk -F'=' '!seen[$$1]++' | tail -r > .env.clean && mv .env.clean .env
	@echo "Appended real dev AWS resource identifiers to .env"

##################################################
# Lint / Format
##################################################

format: ## Format code
	$(PY_RUN_CMD) ruff format $(FMT_ARGS) . $(POSTMAN_DIR)

lint: ## Run all linters
lint: lint-ruff lint-uv lint-mypy

lint-ruff: ## Lint Python code with ruff
	$(PY_RUN_CMD) ruff check $(LINT_ARGS) . $(POSTMAN_DIR)

lint-mypy: ## Type check with mypy
	$(PY_RUN_CMD) mypy src tests $(POSTMAN_DIR)

lint-uv: ## Check uv lockfile is up-to-date
	$(RUN_CMD) uv lock --check

##################################################
# Miscellaneous Utilities
##################################################

login: start ## Start shell in running container
	docker exec -it $(APP_NAME) bash

clean: ## Clean build artifacts
	rm -rf .pytest_cache .coverage_report .coverage __pycache__
	find . -type d -name "__pycache__" -exec rm -rf {} +

api-key: ## Mint an API key (NAME=client ENVIRONMENT=dev TENANT=tenant-id [EXPIRES=ISO8601]).
# Runs natively (not in container) - needs host AWS credentials for DynamoDB.
# Example usage:
#   make api-key NAME=my-client ENVIRONMENT=dev TENANT=my-tenant
#   make api-key NAME=my-client ENVIRONMENT=dev TENANT=my-tenant EXPIRES=2026-12-31T23:59:59Z
	@:$(call check_defined, NAME, client name, e.g. NAME=my-client)
	@:$(call check_defined, ENVIRONMENT, environment, e.g. ENVIRONMENT=dev)
	@:$(call check_defined, TENANT, tenant ID, e.g. TENANT=my-tenant)
	$(AWS_RUN_CMD) api-keys generate --api-key-name "$(NAME)" --environment "$(ENVIRONMENT)" --tenant-id "$(TENANT)" $(if $(EXPIRES),--expires-at "$(EXPIRES)",)

api-key-list: ## List API keys ([NAME=client] [INCLUDE_INACTIVE=1]).
	$(AWS_RUN_CMD) api-keys list $(if $(NAME),--api-key-name "$(NAME)",) $(if $(INCLUDE_INACTIVE),--include-inactive,)

api-key-deactivate: ## Deactivate API key(s) (NAME=client [API_KEY=key] [ALL=1]).
	@:$(call check_defined, NAME, client name, e.g. NAME=my-client)
	$(AWS_RUN_CMD) api-keys deactivate --api-key-name "$(NAME)" $(if $(API_KEY),--api-key "$(API_KEY)",) $(if $(ALL),--all,)

tenant: ## Create a tenant (TENANT=tenant-id DISPLAY_NAME="name" [CONTACT=email] [CONFIDENCE_FLOOR=0.8]).
# Runs natively (not in container) - needs host AWS credentials for DynamoDB.
# Example usage:
#   make tenant TENANT=my-tenant DISPLAY_NAME="My Tenant"
	@:$(call check_defined, TENANT, tenant ID, e.g. TENANT=my-tenant)
	@:$(call check_defined, DISPLAY_NAME, display name, e.g. DISPLAY_NAME="My Tenant")
	$(AWS_RUN_CMD) tenants create --tenant-id "$(TENANT)" --display-name "$(DISPLAY_NAME)" $(if $(CONTACT),--primary-contact "$(CONTACT)",) $(if $(CONFIDENCE_FLOOR),--extraction-confidence-floor "$(CONFIDENCE_FLOOR)",)

tenant-list: ## List tenants ([INCLUDE_INACTIVE=1]).
	$(AWS_RUN_CMD) tenants list $(if $(INCLUDE_INACTIVE),--include-inactive,)

tenant-deactivate: ## Deactivate a tenant (TENANT=tenant-id).
	@:$(call check_defined, TENANT, tenant ID, e.g. TENANT=my-tenant)
	$(AWS_RUN_CMD) tenants deactivate --tenant-id "$(TENANT)"

pull-blueprint-fields: ## Write blueprint field labels (ARN=project-arn required)
	@:$(call check_defined, ARN, BDA project ARN, e.g. ARN=arn:aws:bedrock:us-east-1:123:data-automation-project/abc)
	$(AWS_RUN_CMD) pull-blueprint-fields --project-arn "$(ARN)"

pull-blueprint-schemas: ## Preload BDA blueprint schemas into the static schemas file get_all_schemas() reads
	@test -f .env || (echo ".env not found - run 'make setup-env' and 'make env-from-aws' first" && exit 1)
	@set -a && . ./.env && set +a && $(AWS_RUN_CMD) pull-blueprint-schemas write

check-blueprint-schemas: ## Verify blueprint_schemas.json matches infra/document-types/ custom blueprints (no AWS creds needed)
	$(AWS_RUN_CMD) pull-blueprint-schemas check

generate-categories: ## Regenerate the PreclassificationCategory enum from infra/document-types/ folder names
	$(AWS_RUN_CMD) generate-categories

metrics-agg: ## Aggregate metrics for a date or range (DATE=YYYY-MM-DD [END=YYYY-MM-DD] [OVERWRITE=1])
	@:$(call check_defined, DATE, target date, e.g. DATE=2025-01-15)
	$(if $(END), \
		$(AWS_RUN_CMD) metrics_aggregator backfill "$(DATE)" "$(END)" $(if $(OVERWRITE),--overwrite,), \
		$(AWS_RUN_CMD) metrics_aggregator cli "$(DATE)" $(if $(OVERWRITE),--overwrite,))

metrics-agg-last-n-days: ## Aggregate metrics for the last N days (DAYS=7 [OVERWRITE=1])
	@:$(call check_defined, DAYS, number of days, e.g. DAYS=7)
	$(AWS_RUN_CMD) metrics_aggregator backfill \
		"$(shell date -v-$(DAYS)d +%Y-%m-%d)" \
		"$(shell date +%Y-%m-%d)" \
		$(if $(OVERWRITE),--overwrite,)

usage-report: ## Generate tenant usage report (MONTH=YYYY-MM required)
	@:$(call check_defined, MONTH, target month, e.g. MONTH=2026-01)
	@:$(call check_defined, DDB_EXPORT_BUCKET_NAME, metrics bucket name)
	@:$(call check_defined, GLUE_DATABASE_NAME, Glue database name)
	@:$(call check_defined, DDB_RAW_DATA_TABLE_NAME, Glue table name)
	@:$(call check_defined, ATHENA_WORKGROUP_NAME, Athena workgroup name)
	$(AWS_RUN_CMD) usage_report "$(MONTH)"

openapi-spec: ## Export openapi spec to docs directory and regenerate Postman collection
	$(PY_RUN_CMD) export-openapi > $(APP_DOCS_DIR)/openapi.json
	$(MAKE) postman

postman: ## Regenerate the Postman collection from openapi.json
	$(APP_DOCS_DIR)/postman/build.sh

diagrams: ## Render all .mmd diagrams to SVG
diagrams: $(DIAGRAMS)

$(APP_DOCS_DIR)/media/%.svg: $(APP_DOCS_DIR)/diagrams/%.mmd
	docker run --rm \
	-v $(APP_DOCS_DIR):/data \
	ghcr.io/mermaid-js/mermaid-cli/mermaid-cli:latest \
	-i diagrams/$*.mmd \
	-o media/$*.svg \
	--iconPacks '@iconify-json/logos' \
	--iconPacks '@iconify-json/material-symbols'

help: ## Show help
	@grep -Eh '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "APP_NAME=$(APP_NAME)"
