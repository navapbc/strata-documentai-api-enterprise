.PHONY: \
	deploy \
	deploy-infra \
	deploy-api \
	deploy-admin-ui \
	deploy-demo-ui \
	deploy-ui \
	record-admin-ui \
	record-rules-ui \
	record-viewer-ui \
	record-demo-ui \
	record-ui \
	record-api-setup \
	playwright-install \
	postman \
	format \
	lint \
	test \
	test-api \
	test-ui \
	secret-scan \
	install-hooks \
	adr-log \
	help

.DEFAULT_GOAL := help

ENVIRONMENT ?= dev
AWS_PROFILE ?= nava-sandbox
AWS_ARGS := --profile $(AWS_PROFILE)
TF_DIR := infra/environments/$(ENVIRONMENT)
MEDIA_DIR := docs/documentai-api/media

deploy: ## Deploy everything (infra + UIs)
deploy: deploy-infra deploy-ui

deploy-infra: ## Deploy infrastructure (Docker image + Terraform)
	$(MAKE) -C infra infra-deploy ENVIRONMENT=$(ENVIRONMENT) AWS_PROFILE=$(AWS_PROFILE)

deploy-api: ## Build and deploy API from current working directory
	$(MAKE) -C infra infra-deploy ENVIRONMENT=$(ENVIRONMENT) AWS_PROFILE=$(AWS_PROFILE) IMAGE_TAG=$(ENVIRONMENT)-$$(date +%s)

deploy-ui: ## Build and deploy both UIs
deploy-ui: deploy-admin-ui deploy-demo-ui

deploy-admin-ui: ## Build admin UI and sync to S3 + invalidate CloudFront
	@echo "Building admin UI..."
	cd ui/admin && npm run build
	@BUCKET=$$(terraform -chdir="$(TF_DIR)" output -raw admin_ui_bucket) && \
	DIST_ID=$$(terraform -chdir="$(TF_DIR)" output -raw admin_ui_distribution_id) && \
	echo "Syncing to s3://$$BUCKET..." && \
	aws s3 sync ui/admin/ s3://$$BUCKET \
		--exclude "*" \
		--include "index.html" \
		--include "config.json" \
		--include "favicon.svg" \
		--include "dist/*" \
		--include "styles/*" \
		$(AWS_ARGS) \
		--delete && \
	echo "Invalidating CloudFront cache..." && \
	aws cloudfront create-invalidation \
		--distribution-id $$DIST_ID \
		--paths "/*" \
		$(AWS_ARGS) \
		--no-cli-pager && \
	echo "Admin UI deployed."

deploy-demo-ui: ## Build demo UI and sync to S3 + invalidate CloudFront
	@echo "Building demo UI..."
	cd ui/demo && npm run build
	@BUCKET=$$(terraform -chdir="$(TF_DIR)" output -raw demo_ui_bucket) && \
	DIST_ID=$$(terraform -chdir="$(TF_DIR)" output -raw demo_ui_distribution_id) && \
	echo "Syncing to s3://$$BUCKET..." && \
	aws s3 sync ui/demo/ s3://$$BUCKET \
		--exclude "*" \
		--include "index.html" \
		--include "config.json" \
		--include "favicon.svg" \
		--include "dist/*" \
		--include "styles/*" \
		$(AWS_ARGS) \
		--delete && \
	echo "Invalidating CloudFront cache..." && \
	aws cloudfront create-invalidation \
		--distribution-id $$DIST_ID \
		--paths "/*" \
		$(AWS_ARGS) \
		--no-cli-pager && \
	echo "Demo UI deployed."

record-ui: ## Regenerate demo videos for both UIs (webm + gif)
record-ui: record-admin-ui record-rules-ui record-viewer-ui record-demo-ui

playwright-install: ## Install Playwright Chromium browser for both UIs
	cd ui/admin && npx playwright install chromium
	cd ui/demo && npx playwright install chromium

record-admin-ui: ## Record admin console walkthrough video -> $(MEDIA_DIR)/admin-walkthrough.gif
record-admin-ui: playwright-install
	@which ffmpeg > /dev/null 2>&1 || (echo "Error: ffmpeg not found. Install with: brew install ffmpeg" && exit 1)
	cd ui/admin && npm run record -- --grep "admin console"
	ui/shared/scripts/webm-to-gif.sh ui/admin/video-output/*/video.webm $(MEDIA_DIR)/admin-walkthrough.gif

record-rules-ui: ## Record extraction rules walkthrough video -> $(MEDIA_DIR)/admin-extraction-rules-walkthrough.gif
record-rules-ui: playwright-install
	@which ffmpeg > /dev/null 2>&1 || (echo "Error: ffmpeg not found. Install with: brew install ffmpeg" && exit 1)
	cd ui/admin && npm run record -- --grep "extraction rules"
	ui/shared/scripts/webm-to-gif.sh ui/admin/video-output/*/video.webm $(MEDIA_DIR)/admin-extraction-rules-walkthrough.gif

record-viewer-ui: ## Record document viewer walkthrough video -> $(MEDIA_DIR)/document-viewer-walkthrough.gif
record-viewer-ui: playwright-install
	@which ffmpeg > /dev/null 2>&1 || (echo "Error: ffmpeg not found. Install with: brew install ffmpeg" && exit 1)
	cd ui/admin && npm run record -- --grep "document viewer"
	ui/shared/scripts/webm-to-gif.sh ui/admin/video-output/*/video.webm $(MEDIA_DIR)/document-viewer-walkthrough.gif

record-demo-ui: ## Record demo UI walkthrough video -> $(MEDIA_DIR)/demo-walkthrough.gif
record-demo-ui: playwright-install
	@which ffmpeg > /dev/null 2>&1 || (echo "Error: ffmpeg not found. Install with: brew install ffmpeg" && exit 1)
	cd ui/demo && npx playwright test --config=playwright.video.config.js
	ui/shared/scripts/webm-to-gif.sh ui/demo/video-output/*/video.webm $(MEDIA_DIR)/demo-walkthrough.gif

record-api-setup: ## Record local API setup demo -> $(MEDIA_DIR)/api-setup-demo.gif
	@which vhs > /dev/null 2>&1 || (echo "Error: vhs not found. Install with: brew install vhs" && exit 1)
	@which ffmpeg > /dev/null 2>&1 || (echo "Error: ffmpeg not found. Install with: brew install ffmpeg" && exit 1)
	vhs docs/documentai-api/api-setup-demo.tape
	ffmpeg -y -i api-setup-demo.mp4 \
		-filter_complex "[0:v]setpts=PTS/1.0,fps=12,scale=960:-1:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer" \
		$(MEDIA_DIR)/api-setup-demo.gif
	rm -f api-setup-demo.mp4

postman: ## Regenerate the Postman collection from docs/documentai-api/openapi.json
	$(MAKE) -C documentai-api postman

adr-log: ## Regenerate the ADR index (docs/decisions/index.md)
	@which adr-log > /dev/null 2>&1 || (echo "Error: adr-log not found. Install with: npm install -g adr-log" && exit 1)
	cd docs/decisions && adr-log -i -e template.md

help: ## Show help
	@grep -Eh '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "ENVIRONMENT=$(ENVIRONMENT)  AWS_PROFILE=$(AWS_PROFILE)"

format: ## Format all code
	$(MAKE) -C documentai-api format
	cd ui/admin && npm run format
	cd ui/demo && npm run format

lint: ## Run all linters
	$(MAKE) -C documentai-api lint
	cd ui/admin && npm run lint
	cd ui/demo && npm run lint

test: test-api test-ui  ## Run all tests

test-api:  ## Run API tests only
	$(MAKE) -C documentai-api test

test-ui:  ## Run UI tests only
	cd ui/admin && npm test
	cd ui/demo && npm test

secret-scan: ## Scan full git history for secrets (matches CI secret-scan.yml)
	gitleaks git --redact --verbose --log-opts="--all" .

install-hooks: ## Enable the local pre-commit secret scan (.githooks/)
	git config core.hooksPath .githooks
	@echo "Hooks installed. Pre-commit will run gitleaks on staged changes."
