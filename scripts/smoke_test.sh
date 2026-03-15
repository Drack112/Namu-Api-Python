#!/usr/bin/env bash
# =============================================================================
# smoke_test.sh — Full end-to-end smoke test for Namu AI Wellness API
# Logs every request body, response body, status code, timing, and app logs.
# =============================================================================

set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
BASE_URL="${BASE_URL:-http://localhost:8000}"
REDIS_URL="${REDIS_URL:-redis://localhost:6379}"
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"
LOG_DIR="${LOG_DIR:-./logs/smoke}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${LOG_DIR}/smoke_${TIMESTAMP}.log"
APP_LOG_SNAPSHOT="${LOG_DIR}/app_snapshot_${TIMESTAMP}.log"

mkdir -p "$LOG_DIR"

# ── Colors ────────────────────────────────────────────────────────────────────
RESET="\033[0m"
BOLD="\033[1m"
GREEN="\033[0;32m"
RED="\033[0;31m"
YELLOW="\033[0;33m"
CYAN="\033[0;36m"
GRAY="\033[0;90m"

# ── Helpers ───────────────────────────────────────────────────────────────────
log() {
  local msg="$*"
  echo -e "$msg"
  # Strip ANSI codes before writing to file
  echo "$msg" | sed 's/\x1b\[[0-9;]*m//g' >> "$LOG_FILE"
}

separator() {
  log "${GRAY}$(printf '─%.0s' {1..72})${RESET}"
}

section() {
  echo ""
  separator
  log "${BOLD}${CYAN}▶  $1${RESET}"
  separator
}

# $1=method  $2=path  $3=body (optional, pass "" for GET)
# Outputs: HTTP status code; response body is stored in $RESPONSE_BODY
REQUEST_COUNT=0
do_request() {
  local method="$1"
  local path="$2"
  local body="${3:-}"
  local url="${BASE_URL}${path}"

  REQUEST_COUNT=$((REQUEST_COUNT + 1))

  log ""
  log "${BOLD}[#${REQUEST_COUNT}] ${method} ${path}${RESET}"

  if [[ -n "$body" ]]; then
    log "${YELLOW}  ↑ Request body:${RESET}"
    echo "$body" | python3 -m json.tool 2>/dev/null | while IFS= read -r line; do
      log "    ${line}"
    done
  fi

  local start_ns
  start_ns=$(date +%s%N 2>/dev/null || echo "0")

  local tmp_headers tmp_body
  tmp_headers=$(mktemp)
  tmp_body=$(mktemp)

  local curl_args=(
    --silent
    --show-error
    --location            # follow 307/308 redirects automatically
    --dump-header "$tmp_headers"
    --output "$tmp_body"
    --write-out "%{http_code}"
    --max-time 360
    -H "Content-Type: application/json"
    -H "Accept: application/json"
    -X "$method"
    "$url"
  )

  if [[ -n "$body" ]]; then
    curl_args+=(--data "$body")
  fi

  local http_code
  http_code=$(curl "${curl_args[@]}" 2>&1) || {
    log "${RED}  ✗ curl failed — is the server running at ${BASE_URL}?${RESET}"
    rm -f "$tmp_headers" "$tmp_body"
    RESPONSE_BODY=""
    HTTP_STATUS="000"
    return 1
  }

  local end_ns
  end_ns=$(date +%s%N 2>/dev/null || echo "0")
  local elapsed_ms=$(( (end_ns - start_ns) / 1000000 ))

  RESPONSE_BODY=$(cat "$tmp_body")
  HTTP_STATUS="$http_code"

  # Status colour
  local status_color="$GREEN"
  [[ "$http_code" -ge 400 ]] && status_color="$RED"
  [[ "$http_code" -ge 300 && "$http_code" -lt 400 ]] && status_color="$YELLOW"

  log "${status_color}  ↓ HTTP ${http_code}${RESET}  ${GRAY}(${elapsed_ms} ms)${RESET}"

  # Response headers (trimmed)
  log "${GRAY}  ── Response headers ──${RESET}"
  grep -E "^(content-type|x-|location|set-cookie):" "$tmp_headers" \
    | while IFS= read -r hline; do log "    ${GRAY}${hline}${RESET}"; done || true

  # Pretty-print JSON response
  local pretty
  pretty=$(echo "$RESPONSE_BODY" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE_BODY")
  log "${YELLOW}  ↓ Response body:${RESET}"
  echo "$pretty" | while IFS= read -r line; do log "    ${line}"; done

  rm -f "$tmp_headers" "$tmp_body"

  # Fail loudly on 5xx
  if [[ "$http_code" -ge 500 ]]; then
    log "${RED}  ✗ Server error (5xx) — aborting${RESET}"
    return 1
  fi
}

# Extract a JSON field with python (no jq dependency)
json_field() {
  python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('$1',''))" <<< "$1" 2>/dev/null || true
  python3 -c "import sys,json; print(json.loads(sys.stdin.read()).get('$2',''))" <<< "$1"
}

extract() {
  # $1=json string  $2=key
  python3 -c "import sys,json; print(json.loads('''$1''').get('$2',''))" 2>/dev/null || echo ""
}

# redis_check $key — inspects a Redis key via redis-cli and logs the result
redis_check() {
  local key="$1"
  local cli_bin

  # Locate redis-cli (direct install or Docker)
  if command -v redis-cli &>/dev/null; then
    cli_bin="redis-cli -h ${REDIS_HOST} -p ${REDIS_PORT}"
  elif command -v docker &>/dev/null && docker ps --format '{{.Names}}' 2>/dev/null | grep -qi redis; then
    local container
    container=$(docker ps --format '{{.Names}}' | grep -i redis | head -1)
    cli_bin="docker exec ${container} redis-cli"
  else
    log "${YELLOW}  ⚠ redis-cli not found and no Redis container detected — skipping Redis check${RESET}"
    return 0
  fi

  log "${CYAN}  ── Redis inspection: ${key} ──${RESET}"

  # EXISTS
  local exists
  exists=$($cli_bin EXISTS "$key" 2>/dev/null || echo "ERR")
  if [[ "$exists" == "ERR" ]]; then
    log "${RED}    redis-cli error — cannot connect to Redis at ${REDIS_HOST}:${REDIS_PORT}${RESET}"
    return 0
  fi
  [[ "$exists" == "1" ]] \
    && log "${GREEN}    EXISTS   : 1 (key is present)${RESET}" \
    || log "${RED}    EXISTS   : 0 (key NOT found — cache miss or evicted)${RESET}"

  # TTL
  local ttl
  ttl=$($cli_bin TTL "$key" 2>/dev/null || echo "ERR")
  log "${GRAY}    TTL      : ${ttl}s${RESET}"

  # TYPE
  local ktype
  ktype=$($cli_bin TYPE "$key" 2>/dev/null || echo "ERR")
  log "${GRAY}    TYPE     : ${ktype}${RESET}"

  # VALUE (pretty-print if JSON)
  if [[ "$exists" == "1" ]]; then
    local raw
    raw=$($cli_bin GET "$key" 2>/dev/null || echo "")
    local pretty
    pretty=$(echo "$raw" | python3 -m json.tool 2>/dev/null || echo "$raw")
    log "${GRAY}    VALUE    :${RESET}"
    echo "$pretty" | while IFS= read -r line; do log "    ${GRAY}  ${line}${RESET}"; done
  fi
}

# ── Banner ────────────────────────────────────────────────────────────────────
clear
log "${BOLD}${CYAN}"
log "╔══════════════════════════════════════════════════════════════════════╗"
log "║          Namu AI Wellness API  —  Full Smoke Test Suite             ║"
log "╚══════════════════════════════════════════════════════════════════════╝${RESET}"
log "${GRAY}  Base URL  : ${BASE_URL}${RESET}"
log "${GRAY}  Redis     : ${REDIS_HOST}:${REDIS_PORT}${RESET}"
log "${GRAY}  Log file  : ${LOG_FILE}${RESET}"
log "${GRAY}  Started   : $(date)${RESET}"

# ── 0. Health check ───────────────────────────────────────────────────────────
section "0 · Health Check"
do_request GET /health
[[ "$HTTP_STATUS" == "200" ]] || { log "${RED}API is not healthy — stopping.${RESET}"; exit 1; }
log "${GREEN}  ✔ API is up${RESET}"

# ── 1. Create user ────────────────────────────────────────────────────────────
section "1 · Create User"
CREATE_USER_BODY='{
  "name": "Smoke Test User",
  "age": 30,
  "goals": ["reduzir estresse", "melhorar qualidade do sono"],
  "restrictions": "sem restrições físicas",
  "experience_level": "intermediário"
}'
do_request POST /users/ "$CREATE_USER_BODY"

USER_ID=$(extract "$RESPONSE_BODY" id)
if [[ -z "$USER_ID" || "$USER_ID" == "None" ]]; then
  log "${RED}  ✗ Could not extract user_id from response${RESET}"
  exit 1
fi
log "${GREEN}  ✔ User created — id=${USER_ID}${RESET}"

# ── 2. Get user (cache miss then hit) ────────────────────────────────────────
section "2 · Get User  (first call — populates cache)"
do_request GET "/users/${USER_ID}"
log "${GREEN}  ✔ User fetched${RESET}"
redis_check "user:${USER_ID}"

section "2b · Get User  (second call = cache hit)"
do_request GET "/users/${USER_ID}"
log "${GREEN}  ✔ Cache hit confirmed${RESET}"
redis_check "user:${USER_ID}"

# ── 3. Generate recommendation ───────────────────────────────────────────────
section "3 · Generate Recommendation"
REC_BODY="{
  \"user_id\": ${USER_ID},
  \"context\": \"Estou com pouco tempo hoje, prefiro atividades curtas e relaxantes\"
}"
do_request POST /recommendations "$REC_BODY"

REC_ID=$(extract "$RESPONSE_BODY" id)
if [[ -z "$REC_ID" || "$REC_ID" == "None" ]]; then
  log "${RED}  ✗ Could not extract recommendation_id from response${RESET}"
  exit 1
fi
log "${GREEN}  ✔ Recommendation created — id=${REC_ID}${RESET}"

# ── 4. Submit feedback ────────────────────────────────────────────────────────
section "4 · Submit Feedback (rating=5)"
FEEDBACK_BODY='{
  "rating": 5,
  "comment": "Ótimas sugestões, muito pertinentes para o meu dia!"
}'
do_request POST "/recommendations/${REC_ID}/feedback" "$FEEDBACK_BODY"
log "${GREEN}  ✔ Feedback submitted${RESET}"

# ── 5. Second recommendation (feedback pipeline active) ──────────────────────
section "5 · Generate Second Recommendation  (feedback pipeline enrichment)"
REC_BODY2="{
  \"user_id\": ${USER_ID},
  \"context\": \"Hoje estou com mais energia, posso fazer algo mais intenso\"
}"
do_request POST /recommendations "$REC_BODY2"
REC_ID2=$(extract "$RESPONSE_BODY" id)
log "${GREEN}  ✔ Second recommendation — id=${REC_ID2}${RESET}"

# ── 6. Submit feedback with low rating ───────────────────────────────────────
section "6 · Submit Feedback (rating=2, with comment)"
FEEDBACK_BODY2='{
  "rating": 2,
  "comment": "Muito intenso para o meu nível atual, prefiro algo mais suave"
}'
do_request POST "/recommendations/${REC_ID2}/feedback" "$FEEDBACK_BODY2"
log "${GREEN}  ✔ Low-rating feedback submitted${RESET}"

# ── 7. Recommendation history ─────────────────────────────────────────────────
section "7 · Recommendation History"
do_request GET "/users/${USER_ID}/recommendations"
log "${GREEN}  ✔ History retrieved${RESET}"

# ── 8. Error paths ────────────────────────────────────────────────────────────
section "8a · Error — Get non-existent user (expect 404)"
set +e
do_request GET "/users/999999"
set -e
[[ "$HTTP_STATUS" == "404" ]] && log "${GREEN}  ✔ 404 as expected${RESET}" \
  || log "${YELLOW}  ⚠ Expected 404, got ${HTTP_STATUS}${RESET}"

section "8b · Error — Create user with invalid payload (expect 422)"
BAD_USER_BODY='{"name": "", "age": 200, "goals": [], "experience_level": "guru"}'
set +e
do_request POST /users "$BAD_USER_BODY"
set -e
[[ "$HTTP_STATUS" == "422" ]] && log "${GREEN}  ✔ 422 validation error as expected${RESET}" \
  || log "${YELLOW}  ⚠ Expected 422, got ${HTTP_STATUS}${RESET}"

section "8c · Error — Feedback out of range (expect 422)"
BAD_FEEDBACK='{"rating": 99}'
set +e
do_request POST "/recommendations/${REC_ID}/feedback" "$BAD_FEEDBACK"
set -e
[[ "$HTTP_STATUS" == "422" ]] && log "${GREEN}  ✔ 422 validation error as expected${RESET}" \
  || log "${YELLOW}  ⚠ Expected 422, got ${HTTP_STATUS}${RESET}"

# ── 9. Capture app log snapshot ──────────────────────────────────────────────
section "9 · App Log Snapshot"
LATEST_LOG=$(ls -t logs/server_*.log 2>/dev/null | head -1 || true)
if [[ -n "$LATEST_LOG" ]]; then
  cp "$LATEST_LOG" "$APP_LOG_SNAPSHOT"
  log "${GREEN}  ✔ App log copied → ${APP_LOG_SNAPSHOT}${RESET}"
  log "${GRAY}  Last 30 lines of app log:${RESET}"
  tail -30 "$LATEST_LOG" | while IFS= read -r line; do log "    ${GRAY}${line}${RESET}"; done
else
  log "${YELLOW}  ⚠ No app server log found in ./logs/ — skipping snapshot${RESET}"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
separator
echo ""
log "${BOLD}${GREEN}✔  Smoke test completed${RESET}"
log "${GRAY}  Requests made : ${REQUEST_COUNT}${RESET}"
log "${GRAY}  Full log      : ${LOG_FILE}${RESET}"
[[ -n "${LATEST_LOG:-}" ]] && log "${GRAY}  App log copy  : ${APP_LOG_SNAPSHOT}${RESET}"
log "${GRAY}  Finished      : $(date)${RESET}"
echo ""
