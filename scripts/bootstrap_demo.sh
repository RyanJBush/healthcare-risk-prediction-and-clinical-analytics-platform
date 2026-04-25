#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE:-http://localhost:8000}"
ADMIN_USER="${ADMIN_USER:-admin}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin123}"
SEED_COUNT="${SEED_COUNT:-50}"
SEED_VALUE="${SEED_VALUE:-42}"

if ! command -v curl >/dev/null 2>&1; then
  echo "Error: curl is required." >&2
  exit 1
fi

if ! command -v python >/dev/null 2>&1; then
  echo "Error: python is required for JSON parsing." >&2
  exit 1
fi

echo "[1/4] Logging in as ${ADMIN_USER} against ${API_BASE}..."
LOGIN_PAYLOAD=$(printf '{"username":"%s","password":"%s"}' "$ADMIN_USER" "$ADMIN_PASSWORD")
TOKEN=$(curl -sS -X POST "${API_BASE}/auth/login" \
  -H 'Content-Type: application/json' \
  -d "$LOGIN_PAYLOAD" | python -c 'import json,sys; print(json.load(sys.stdin).get("access_token",""))')

if [[ -z "$TOKEN" ]]; then
  echo "Error: could not obtain access token. Is backend running?" >&2
  exit 1
fi

echo "[2/4] Loading synthetic seed dataset (count=${SEED_COUNT}, seed=${SEED_VALUE})..."
SEED_PAYLOAD=$(printf '{"count":%s,"seed":%s}' "$SEED_COUNT" "$SEED_VALUE")
curl -sS -X POST "${API_BASE}/api/demo/load-seed" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H 'Content-Type: application/json' \
  -d "$SEED_PAYLOAD" >/dev/null

echo "[3/4] Running batch scoring for readmission risk..."
curl -sS -X POST "${API_BASE}/api/jobs/batch-score" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H 'Content-Type: application/json' \
  -d '{"target_type":"readmission","limit":200}' >/dev/null

echo "[4/4] Fetching summary metrics..."
curl -sS "${API_BASE}/api/metrics/summary" \
  -H "Authorization: Bearer ${TOKEN}" | python -m json.tool

echo "Demo bootstrap complete."
