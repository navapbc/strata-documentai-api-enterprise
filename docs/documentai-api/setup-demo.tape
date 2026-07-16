# DocumentAI API — local setup from scratch (VHS tape)
# Records the exact documented steps: clone -> .env -> make init -> make start -> curl.
# Run from an empty directory:  vhs setup-demo.tape
# Produces setup-demo.mp4 (faithful full run). Derive a short GIF with:
#   ffmpeg -i setup-demo.mp4 -filter_complex \
#     "[0:v]setpts=PTS/SPEED,fps=12,scale=960:-1:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer" \
#     setup-demo.gif

Output setup-demo.mp4

Require git
Require docker
Require make

Set Shell "bash"
Set FontSize 18
Set Width 1280
Set Height 720
Set Padding 24
Set TypingSpeed 45ms
Set WaitTimeout 900s
Set WaitPattern /demo \$$/

# --- clean, controlled prompt (hidden setup, not part of the demo) ---
Hide
Type "export PS1='demo $ '" Enter
Sleep 800ms
Type "rm -rf strata-documentai-api-enterprise .env" Enter
Sleep 800ms
Type "clear" Enter
Sleep 800ms
Show

# --- 1. clone the repo ---
Type "git clone -b lgoolsby/update-documentation https://github.com/navapbc/strata-documentai-api-enterprise.git"
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

# --- 4. build the container image ---
Type "make init"
Sleep 400ms
Enter
Wait

# --- 5. start the API ---
Type "make start"
Sleep 400ms
Enter
Wait

# wait for the server to be ready (hidden readiness poll)
Hide
Type "until curl -sf localhost:8000/health >/dev/null; do sleep 1; done" Enter
Wait
Show

# --- 6. hit the endpoints ---
Type "curl -s localhost:8000/health | jq"
Sleep 400ms
Enter
Wait
Sleep 1500ms

Type 'curl -s -H "API-Key: local-dev-key" localhost:8000/v1/me | jq'
Sleep 400ms
Enter
Wait
Sleep 3s

# --- teardown (hidden) ---
Hide
Type "make stop" Enter
Wait
Show
