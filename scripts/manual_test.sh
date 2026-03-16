#!/bin/bash
# scripts/manual_test.sh

set -e

API_URL="${API_URL:-http://localhost:8000}"
ITTS_SAMPLE_PATH="${ITTS_SAMPLE_PATH:-tests/fixtures/spk_1772197182_1772197202988.itts}"

echo "=== ITTS Backend Manual Test Suite ==="

if [ ! -f "$ITTS_SAMPLE_PATH" ]; then
  echo "Sample ITTS file not found: $ITTS_SAMPLE_PATH"
  echo "Set ITTS_SAMPLE_PATH to a local .itts file before running this script."
  exit 1
fi

# 1. Health check
echo "[1] Health check..."
curl -s "$API_URL/health" | jq '.'

# 2. Upload bundle
echo "[2] Uploading sample ITTS..."
UPLOAD_RAW=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/api/bundles" \
  -F "file=@$ITTS_SAMPLE_PATH")
UPLOAD_BODY=$(echo "$UPLOAD_RAW" | sed '$d')
UPLOAD_STATUS=$(echo "$UPLOAD_RAW" | tail -n 1)

if [ "$UPLOAD_STATUS" = "201" ]; then
  BUNDLE_ID=$(echo "$UPLOAD_BODY" | jq -r '.id')
elif [ "$UPLOAD_STATUS" = "409" ]; then
  DUP_STATUS=$(echo "$UPLOAD_BODY" | jq -r '.detail.status')
  if [ "$DUP_STATUS" != "duplicate" ]; then
    echo "Upload failed with unexpected 409 payload"
    echo "$UPLOAD_BODY"
    exit 1
  fi
  BUNDLE_ID=$(echo "$UPLOAD_BODY" | jq -r '.detail.existing_bundle.id')
else
  echo "Upload failed with status: $UPLOAD_STATUS"
  echo "$UPLOAD_BODY"
  exit 1
fi

if [ -z "$BUNDLE_ID" ] || [ "$BUNDLE_ID" = "null" ]; then
  echo "Failed to resolve bundle ID from upload response"
  exit 1
fi

echo "Using bundle ID: $BUNDLE_ID"

# 3. List bundles
echo "[3] Listing all bundles..."
curl -s "$API_URL/api/bundles" | jq '.'

# 4. Get bundle
echo "[4] Getting bundle $BUNDLE_ID..."
curl -s "$API_URL/api/bundles/$BUNDLE_ID" | jq '.'

# 5. Get segments
echo "[5] Getting segments..."
curl -s "$API_URL/api/bundles/$BUNDLE_ID/segments" | jq '.'

# 6. Search
echo "[6] Searching for sample1..."
curl -s "$API_URL/api/search?emotion=sample1" | jq '.'

# 7. List playlists
echo "[7] Listing playlists..."
curl -s "$API_URL/api/playlists" | jq '.'

# 8. Create export
echo "[8] Creating export..."
EXPORT=$(curl -s -X POST "$API_URL/api/export" \
  -H "Content-Type: application/json" \
  -d "{\"bundle_id\": $BUNDLE_ID, \"segment_indices\": [0], \"silence_ms\": 100}" \
  -w "\n%{http_code}")
EXPORT_BODY=$(echo "$EXPORT" | sed '$d')
EXPORT_STATUS=$(echo "$EXPORT" | tail -n 1)

if [ "$EXPORT_STATUS" != "201" ]; then
  echo "Export creation failed with status: $EXPORT_STATUS"
  echo "$EXPORT_BODY"
  exit 1
fi

JOB_ID=$(echo "$EXPORT_BODY" | jq -r '.job_id')
if [ -z "$JOB_ID" ] || [ "$JOB_ID" = "null" ]; then
  echo "Failed to resolve export job_id"
  exit 1
fi
echo "Export job created: $JOB_ID"

# 9. Poll for completion
echo "[9] Waiting for export to complete..."
for i in {1..10}; do
  STATUS=$(curl -s "$API_URL/api/jobs/$JOB_ID" | jq -r '.status')
  if [ "$STATUS" == "completed" ]; then
    echo "Export completed"
    COMPLETED=1
    break
  fi
  sleep 1
done

if [ "${COMPLETED:-0}" != "1" ]; then
  echo "Export job did not complete in time"
  exit 1
fi

# 10. List backups
echo "[10] Listing backups..."
curl -s "$API_URL/api/backups" | jq '.'

echo "=== All tests passed ==="
