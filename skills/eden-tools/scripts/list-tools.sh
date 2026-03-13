#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=skills/eden-tools/scripts/lib.sh
source "$SCRIPT_DIR/lib.sh"

eden_require_command curl
eden_require_command node

LIMIT=50
COMPACT=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --limit)
      LIMIT="$2"
      shift 2
      ;;
    --compact)
      COMPACT=1
      shift
      ;;
    *)
      echo "eden-tools: unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

TMP_DIR="$(eden_make_tmpdir)"
trap 'rm -rf "$TMP_DIR"' EXIT

RESPONSE_FILE="$TMP_DIR/tools.json"
STATUS_CODE="$(eden_curl_json GET "/v1/tools?limit=$LIMIT" "" "$RESPONSE_FILE")"

if [[ "$STATUS_CODE" -lt 200 || "$STATUS_CODE" -ge 300 ]]; then
  eden_fail_response "$STATUS_CODE" "$RESPONSE_FILE"
fi

eden_pretty_json_file "$RESPONSE_FILE" "$COMPACT"

