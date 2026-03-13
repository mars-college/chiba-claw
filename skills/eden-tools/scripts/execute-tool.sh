#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=skills/eden-tools/scripts/lib.sh
source "$SCRIPT_DIR/lib.sh"

eden_require_command curl
eden_require_command node

TOOL_ID=""
INLINE_DATA=""
DATA_FILE=""
ARGUMENTS=()
NO_WAIT=0
COMPACT=0
POLL_INTERVAL="${EDEN_POLL_INTERVAL_SECONDS:-2}"
TIMEOUT_SECONDS="${EDEN_TOOL_TIMEOUT_SECONDS:-300}"

usage() {
  cat >&2 <<'EOF'
Usage:
  bash skills/eden-tools/scripts/execute-tool.sh --tool-id fal/nano-banana --arg prompt="banana dj" --arg num_images=2

Options:
  --tool-id <id>        Eden tool id. Slash ids use the compound execute route.
  --arg <key=value>     Tool argument. Repeated flags build the input object.
  --data <json>         Raw tool input object as inline JSON.
  --data-file <path>    File containing the raw tool input object as JSON.
  --no-wait             Return the immediate execute response without polling.
  --poll-interval <s>   Poll interval in seconds when waiting for task-like responses.
  --timeout <s>         Max seconds to wait for terminal task status.
  --compact             Print compact JSON instead of pretty JSON.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tool-id)
      TOOL_ID="$2"
      shift 2
      ;;
    --data)
      INLINE_DATA="$2"
      shift 2
      ;;
    --data-file)
      DATA_FILE="$2"
      shift 2
      ;;
    --arg)
      ARGUMENTS+=("$2")
      shift 2
      ;;
    --no-wait)
      NO_WAIT=1
      shift
      ;;
    --poll-interval)
      POLL_INTERVAL="$2"
      shift 2
      ;;
    --timeout)
      TIMEOUT_SECONDS="$2"
      shift 2
      ;;
    --compact)
      COMPACT=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "eden-tools: unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$TOOL_ID" ]]; then
  echo "eden-tools: --tool-id is required" >&2
  usage
  exit 1
fi

if [[ -n "$INLINE_DATA" && -n "$DATA_FILE" ]]; then
  echo "eden-tools: use either --data or --data-file, not both" >&2
  exit 1
fi

if [[ ${#ARGUMENTS[@]} -gt 0 && ( -n "$INLINE_DATA" || -n "$DATA_FILE" ) ]]; then
  echo "eden-tools: use either --arg flags, --data, or --data-file" >&2
  exit 1
fi

TMP_DIR="$(eden_make_tmpdir)"
trap 'rm -rf "$TMP_DIR"' EXIT

RAW_INPUT_FILE="$TMP_DIR/input.json"
WRAPPED_BODY_FILE="$TMP_DIR/body.json"
INITIAL_RESPONSE_FILE="$TMP_DIR/initial.json"
POLL_RESPONSE_FILE="$TMP_DIR/poll.json"

if [[ -n "$DATA_FILE" ]]; then
  cp "$DATA_FILE" "$RAW_INPUT_FILE"
elif [[ -n "$INLINE_DATA" ]]; then
  printf "%s" "$INLINE_DATA" >"$RAW_INPUT_FILE"
elif [[ ${#ARGUMENTS[@]} -gt 0 ]]; then
  node - "$RAW_INPUT_FILE" "${ARGUMENTS[@]}" <<'NODE'
const fs = require("fs");

const outputFile = process.argv[2];
const args = process.argv.slice(3);
const payload = {};

for (const entry of args) {
  const separator = entry.indexOf("=");
  if (separator <= 0) {
    throw new Error(`Invalid --arg value: ${entry}. Expected key=value.`);
  }

  const key = entry.slice(0, separator);
  const rawValue = entry.slice(separator + 1);
  let parsedValue;

  try {
    parsedValue = JSON.parse(rawValue);
  } catch {
    parsedValue = rawValue;
  }

  payload[key] = parsedValue;
}

fs.writeFileSync(outputFile, JSON.stringify(payload));
NODE
else
  printf "{}" >"$RAW_INPUT_FILE"
fi

eden_write_wrapped_body "$RAW_INPUT_FILE" "$WRAPPED_BODY_FILE"

if [[ "$TOOL_ID" == */* ]]; then
  PROVIDER="${TOOL_ID%%/*}"
  PRODUCT="${TOOL_ID#*/}"
  EXECUTE_PATH="/v1/tools/$(eden_urlencode "$PROVIDER")/$(eden_urlencode "$PRODUCT")/execute"
else
  EXECUTE_PATH="/v1/tools/$(eden_urlencode "$TOOL_ID")/execute"
fi

STATUS_CODE="$(eden_curl_json POST "$EXECUTE_PATH" "$WRAPPED_BODY_FILE" "$INITIAL_RESPONSE_FILE")"

if [[ "$STATUS_CODE" -lt 200 || "$STATUS_CODE" -ge 300 ]]; then
  eden_fail_response "$STATUS_CODE" "$INITIAL_RESPONSE_FILE"
fi

if [[ "$NO_WAIT" -eq 1 ]]; then
  eden_pretty_json_file "$INITIAL_RESPONSE_FILE" "$COMPACT"
  exit 0
fi

POLL_TARGET="$(
  node - "$INITIAL_RESPONSE_FILE" <<'NODE'
const fs = require("fs");
const payload = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const pendingStatuses = new Set([
  "queued",
  "pending",
  "running",
  "processing",
  "in_progress",
  "suspended",
]);

function maybeEmit(path) {
  if (typeof path === "string" && path !== "") {
    process.stdout.write(path);
  }
}

if (payload && typeof payload === "object") {
  const rootStatus =
    typeof payload.status === "string" ? payload.status.toLowerCase() : "";
  if (typeof payload.pollUrl === "string") {
    maybeEmit(payload.pollUrl);
  } else if (typeof payload.statusUrl === "string") {
    maybeEmit(payload.statusUrl);
  } else if (typeof payload.status_url === "string") {
    maybeEmit(payload.status_url);
  } else if (
    payload.task &&
    typeof payload.task === "object" &&
    typeof payload.task.id === "string"
  ) {
    maybeEmit(`/v1/tasks/${encodeURIComponent(payload.task.id)}`);
  } else if (typeof payload.taskId === "string") {
    maybeEmit(`/v1/tasks/${encodeURIComponent(payload.taskId)}`);
  } else if (
    typeof payload.id === "string" &&
    pendingStatuses.has(rootStatus) &&
    /^tsk[_-]/i.test(payload.id)
  ) {
    maybeEmit(`/v1/tasks/${encodeURIComponent(payload.id)}`);
  }
}
NODE
)"

if [[ -z "$POLL_TARGET" ]]; then
  eden_print_result_file "$INITIAL_RESPONSE_FILE" "$COMPACT"
  exit 0
fi

START_EPOCH="$(date +%s)"

while true; do
  NOW_EPOCH="$(date +%s)"
  if (( NOW_EPOCH - START_EPOCH > TIMEOUT_SECONDS )); then
    echo "eden-tools: timed out waiting for terminal result from $TOOL_ID" >&2
    eden_pretty_json_file "$INITIAL_RESPONSE_FILE" 0 >&2
    exit 124
  fi

  POLL_STATUS_CODE="$(eden_curl_json GET "$POLL_TARGET" "" "$POLL_RESPONSE_FILE")"
  if [[ "$POLL_STATUS_CODE" -lt 200 || "$POLL_STATUS_CODE" -ge 300 ]]; then
    eden_fail_response "$POLL_STATUS_CODE" "$POLL_RESPONSE_FILE"
  fi

  POLL_STATE="$(
    node - "$POLL_RESPONSE_FILE" <<'NODE'
const fs = require("fs");
const payload = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));

if (payload && typeof payload === "object") {
  if (payload.task && typeof payload.task === "object" && typeof payload.task.status === "string") {
    process.stdout.write(payload.task.status.toLowerCase());
  } else if (typeof payload.status === "string") {
    process.stdout.write(payload.status.toLowerCase());
  }
}
NODE
  )"

  case "$POLL_STATE" in
    completed|succeeded|success|done)
      eden_print_result_file "$POLL_RESPONSE_FILE" "$COMPACT"
      exit 0
      ;;
    failed|error|cancelled|canceled)
      echo "eden-tools: tool $TOOL_ID finished with status $POLL_STATE" >&2
      eden_pretty_json_file "$POLL_RESPONSE_FILE" 0 >&2
      exit 1
      ;;
    "")
      eden_print_result_file "$POLL_RESPONSE_FILE" "$COMPACT"
      exit 0
      ;;
  esac

  sleep "$POLL_INTERVAL"
done
