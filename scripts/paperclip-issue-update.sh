#!/bin/bash
# Paperclip Issue Update Helper
# Usage: ./scripts/paperclip-issue-update.sh --issue-id <id> [--status <status>] [markdown from stdin]

set -e

ISSUE_ID=""
STATUS=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --issue-id)
      ISSUE_ID="$2"
      shift 2
      ;;
    --status)
      STATUS="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

if [[ -z "$ISSUE_ID" ]]; then
  echo "Usage: $0 --issue-id <id> [--status <status>] < comment.md"
  exit 1
fi

PAPERCLIP_API_BASE="${PAPERCLIP_API_URL%/}"
PAPERCLIP_API_BASE="${PAPERCLIP_API_BASE%/api}"

# Read comment from stdin
COMMENT=""
if [[ ! -t 0 ]]; then
  COMMENT=$(cat)
fi

# Build JSON payload
if [[ -n "$STATUS" && -n "$COMMENT" ]]; then
  JSON=$(jq -n \
    --arg status "$STATUS" \
    --arg comment "$COMMENT" \
    '{status: $status, comment: $comment}')
elif [[ -n "$STATUS" ]]; then
  JSON=$(jq -n \
    --arg status "$STATUS" \
    '{status: $status}')
elif [[ -n "$COMMENT" ]]; then
  JSON=$(jq -n \
    --arg comment "$COMMENT" \
    '{comment: $comment}')
else
  echo "Nothing to update"
  exit 1
fi

# Make API call
curl -s -X PATCH \
  -H "Authorization: Bearer $PAPERCLIP_API_KEY" \
  -H "X-Paperclip-Run-Id: $PAPERCLIP_RUN_ID" \
  -H "Content-Type: application/json" \
  -d "$JSON" \
  "$PAPERCLIP_API_BASE/api/issues/$ISSUE_ID" | jq .
