.PHONY: \
	deploy \
	deploy-infra \
	deploy-api \
	deploy-admin-ui \
	deploy-demo-ui \
	deploy-ui \
	record-ui \
	record-api-setup \
	gifs-to-mp4 \
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
	$(MAKE) -C infra infra-deploy ENVIRONMENT=$(ENVIRONMENT) AWS_PROFILE=$(AWS_PROFILE) \
		IMAGE_TAG=$$(git diff --quiet && git diff --cached --quiet \
			&& git rev-parse HEAD \
			|| echo "$$(git rev-parse HEAD)-dirty-$$(date +%s)")

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

record-ui: ## Regenerate UI walkthrough videos. Optional: args=admin-walkthrough-presentation-mode
record-ui: playwright-install
	@which ffmpeg > /dev/null 2>&1 || (echo "Error: ffmpeg not found. Install with: brew install ffmpeg" && exit 1)
	@for spec in ui/admin/e2e-video/*.spec.js ui/demo/e2e-video/*.spec.js; do \
		[ -f "$$spec" ] || continue; \
		stem=$$(basename "$$spec" .spec.js); \
		[ -n "$(args)" ] && [ "$$stem" != "$(args)" ] && continue; \
		echo "--- Recording $$stem ---"; \
		rm -rf ui/admin/video-output ui/demo/video-output; \
		dir=$$(dirname "$$spec"); \
		root=$$(echo "$$dir" | sed 's|/e2e-video||'); \
		( cd $$root && npm run record -- "e2e-video/$$stem.spec.js" ) || exit 1; \
		webm=$$(ls $$root/video-output/*/video.webm 2>/dev/null | head -1); \
		[ -n "$$webm" ] && ui/shared/scripts/webm-to-gif.sh "$$webm" "$(MEDIA_DIR)/$$stem.gif" || echo "Warning: no webm found for $$stem"; \
	done

playwright-install: ## Install Playwright Chromium browser for both UIs
	cd ui/admin && npx playwright install chromium
	cd ui/demo && npx playwright install chromium

gifs-to-mp4: ## Convert all GIFs in $(MEDIA_DIR) to MP4 using ffmpeg
	@which ffmpeg > /dev/null 2>&1 || (echo "Error: ffmpeg not found. Install with: brew install ffmpeg" && exit 1)
	@for gif in $(MEDIA_DIR)/*.gif; do \
		[ -f "$$gif" ] || continue; \
		mp4="$${gif%.gif}.mp4"; \
		echo "Converting $$gif -> $$mp4"; \
		ffmpeg -y -loglevel error -i "$$gif" -movflags faststart -pix_fmt yuv420p -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" "$$mp4"; \
	done

record-api-setup: ## Record local API setup demo -> $(MEDIA_DIR)/api-setup-demo.mp4
	@which vhs > /dev/null 2>&1 || (echo "Error: vhs not found. Install with: brew install vhs" && exit 1)
	vhs docs/documentai-api/api-setup-demo.tape
	mv api-setup-demo.mp4 $(MEDIA_DIR)/api-setup-demo.mp4

postman: ## Regenerate the Postman collection from docs/documentai-api/openapi.json
	$(MAKE) -C documentai-api postman

adr-log: ## Regenerate the ADR index (docs/decisions/index.md)
	@which adr-log > /dev/null 2>&1 || (echo "Error: adr-log not found. Install with: npm install -g adr-log" && exit 1)
	cd docs/decisions && adr-log -i -e template.md

help: ## Show help
	@grep -Eh '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "ENVIRONMENT=$(ENVIRONMENT)  AWS_PROFILE=$(AWS_PROFILE)"

format: ## Format all code
	@which terraform > /dev/null 2>&1 || (echo "Error: terraform not found. Install with: brew install terraform" && exit 1)
	$(MAKE) -C documentai-api format
	$(MAKE) -C infra infra-format
	cd ui/admin && npm run format
	cd ui/demo && npm run format

lint: ## Run all linters
	@which terraform > /dev/null 2>&1 || (echo "Error: terraform not found. Install with: brew install terraform" && exit 1)
	$(MAKE) -C documentai-api lint
	$(MAKE) -C infra infra-lint
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
