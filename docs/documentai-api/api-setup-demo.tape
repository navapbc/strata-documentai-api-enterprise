# DocumentAI API - clone to a real processed document (VHS tape)
#
# The full new-developer path: clone -> .env -> wire in real dev AWS
# resources -> build -> start -> upload -> watch real Bedrock Data
# Automation process it, end to end, all against a local container.
#
# Local docker-compose has no EventBridge/Lambda of its own, but the
# deployed dev environment's S3 -> EventBridge -> Document Processor
# pipeline reacts to any object landing in the real input bucket, no
# matter who uploaded it. So `make env-from-aws` (which points .env at
# real dev resources instead of the documentai-*-local placeholders) is
# enough to get a real end-to-end result from a document posted to the
# local API - no need to hit the deployed API directly.
#
# `make env-from-aws` fetches real resource identifiers (bucket/table/BDA
# ARNs) live and writes them only to the gitignored .env file - its own
# output never prints a real value, so it's safe to show on screen and
# safe to keep this tape committed in this public repo. The upload never
# requests include_extracted_data, hence, no extracted field values are ever
# printed.
#
# Requires: an AWS profile with access to the dev account already exported.
# Run from the repo root with `make record-api-setup` (see top-level
# Makefile) - it invokes this tape and converts the result to
# docs/documentai-api/media/api-setup-demo.gif, which README.md embeds.

Output api-setup-demo.mp4

Require git
Require docker
Require make
Require terraform
Require jq
Require aws
Require curl

Set Shell "bash"
Set FontSize 18
Set Width 1280
Set Height 720
Set Padding 24
Set TypingSpeed 45ms
Set WaitTimeout 300s
Set WaitPattern /demo \$$/

# --- clean, controlled prompt (hidden setup, not part of the demo) ---
Hide
Type "export PS1='demo $ '" Enter
Sleep 800ms
Type "rm -rf strata-documentai-api-enterprise" Enter
Sleep 800ms
Type "clear" Enter
Sleep 800ms
Show

# --- 1. clone the repo ---
Type "git clone https://github.com/navapbc/strata-documentai-api-enterprise.git"
Sleep 600ms
Enter
Wait

# --- 2. into the API package ---
Type "cd strata-documentai-api-enterprise/documentai-api"
Sleep 400ms
Enter
Wait

# --- 3. create the local env file ---
Type "cp local.env.example .env"
Sleep 400ms
Enter
Wait

# --- 4. wire real dev AWS resources into .env ---
# Safe to show - the command's own output never prints real values
# (everything real goes straight into the gitignored .env file).
Type "make env-from-aws"
Sleep 400ms
Enter
Wait
Sleep 3s

# --- 5. build the container image (build log hidden - dead time for a viewer) ---
Type "make init"
Sleep 400ms
Enter
Hide
Wait
Show

# --- 6. start the API ---
Type "make start"
Sleep 400ms
Enter
Wait

# wait for the server to be ready (hidden readiness poll)
Hide
Type "until curl -sf localhost:8000/health >/dev/null; do sleep 1; done" Enter
Wait
Show

# --- 7. sanity check ---
Type "curl -s localhost:8000/health | jq"
Sleep 400ms
Enter
Wait
Sleep 1500ms

Type 'curl -s -H "API-Key: local-dev-key" localhost:8000/v1/me | jq'
Sleep 400ms
Enter
Wait
Sleep 2500ms

# --- 8. real upload - stored in S3, tracked in DynamoDB, queued for BDA ---
Type 'resp=$(curl -s -H "API-Key: local-dev-key" -F "file=@tests/helpers/fixtures/test-documents/synthetic-tax-w2-wage-statement.png" -F "category=tax_documents" localhost:8000/v1/documents)'
Sleep 400ms
Enter
Wait
Sleep 800ms
Type 'echo "$resp" | jq'
Sleep 400ms
Enter
Wait
Sleep 2500ms

Type 'export JOB_ID=$(echo "$resp" | jq -r .jobId)'
Enter
Wait

# --- 9. poll the real pipeline until Bedrock Data Automation finishes ---
Type 'for i in $(seq 1 20); do js=$(curl -s -H "API-Key: local-dev-key" "localhost:8000/v1/documents/$JOB_ID" | jq -r .jobStatus); echo "[$i] $js"; [ "$js" = "completed" -o "$js" = "failed" ] && break; sleep 3; done'
Sleep 400ms
Enter
Wait
Sleep 2500ms

# --- 10. final result - status/classification only, no extracted field values ---
Type 'curl -s -H "API-Key: local-dev-key" "localhost:8000/v1/documents/$JOB_ID" | jq "{jobStatus, matchedDocumentClass, responseCode, responseMessage, totalProcessingTimeSeconds}"'
Sleep 400ms
Enter
Wait
Sleep 6s

# --- teardown (hidden) ---
Hide
Type "make stop" Enter
Wait
Type "cd ../.." Enter
Wait
Type "rm -rf strata-documentai-api-enterprise" Enter
Wait
Show
