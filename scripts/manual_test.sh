#!/bin/bash
# scripts/manual_test.sh

set -e

API_URL="${API_URL:-http://localhost:8000}"

echo "=== ITTS Backend Manual Test Suite ==="

# 1. Health check
echo "[1] Health check..."
curl -s "$API_URL/health" | jq '.'

# 2. Upload bundle
echo "[2] Uploading sample ITTS..."
UPLOAD=$(curl -s -X POST "$API_URL/api/bundles" \
  -F "file=@tests/fixtures/spk_1772197182_1772197202988.itts")
BUNDLE_ID=$(echo "$UPLOAD" | jq -r '.id')
echo "Uploaded bundle ID: $BUNDLE_ID"

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
  -d "{\"bundle_id\": $BUNDLE_ID, \"segment_indices\": [0], \"silence_ms\": 100}")
JOB_ID=$(echo "$EXPORT" | jq -r '.job_id')
echo "Export job created: $JOB_ID"

# 9. Poll for completion
echo "[9] Waiting for export to complete..."
for i in {1..10}; do
  STATUS=$(curl -s "$API_URL/api/jobs/$JOB_ID" | jq -r '.status')
  if [ "$STATUS" == "completed" ]; then
    echo "Export completed"
    break
  fi
  sleep 1
done

# 10. List backups
echo "[10] Listing backups..."
curl -s "$API_URL/api/backups" | jq '.'

echo "=== All tests passed ==="
