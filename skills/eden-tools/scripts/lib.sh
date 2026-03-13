#!/usr/bin/env bash
set -euo pipefail

EDEN_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EDEN_REPO_ROOT="$(cd "$EDEN_LIB_DIR/../../.." && pwd)"
EDEN_ENV_FILE="${CHIBA_CLAW_ENV_FILE:-$EDEN_REPO_ROOT/.env}"

if [[ -f "$EDEN_REPO_ROOT/scripts/load-env.sh" ]]; then
  # shellcheck source=scripts/load-env.sh
  source "$EDEN_REPO_ROOT/scripts/load-env.sh" "$EDEN_ENV_FILE"
elif [[ -f "$EDEN_ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$EDEN_ENV_FILE"
  set +a
fi

eden_source_repo() {
  local source_repo="${EDEN_SOURCE_REPO:-$EDEN_REPO_ROOT/../eden2}"
  printf "%s" "$source_repo"
}

eden_require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "eden-tools: $1 is required" >&2
    exit 1
  fi
}

eden_api_url() {
  local api_url="${EDEN_API_URL:-}"
  if [[ -z "$api_url" ]]; then
    echo "eden-tools: EDEN_API_URL is required" >&2
    exit 1
  fi
  printf "%s" "${api_url%/}"
}

eden_api_key() {
  local api_key="${EDEN_API_KEY:-}"
  if [[ -z "$api_key" ]]; then
    echo "eden-tools: EDEN_API_KEY is required" >&2
    exit 1
  fi
  printf "%s" "$api_key"
}

eden_make_tmpdir() {
  mktemp -d "${TMPDIR:-/tmp}/eden-tools.XXXXXX"
}

eden_urlencode() {
  node -e 'process.stdout.write(encodeURIComponent(process.argv[1]))' "$1"
}

eden_pretty_json_file() {
  local file_path="$1"
  local compact="${2:-0}"
  node - "$file_path" "$compact" <<'NODE'
const fs = require("fs");
const [filePath, compact] = process.argv.slice(2);
const raw = fs.readFileSync(filePath, "utf8");

try {
  const parsed = JSON.parse(raw);
  process.stdout.write(JSON.stringify(parsed, null, compact === "1" ? 0 : 2));
} catch {
  process.stdout.write(raw);
}

if (!raw.endsWith("\n")) {
  process.stdout.write("\n");
}
NODE
}

eden_fail_response() {
  local status_code="$1"
  local response_file="$2"
  echo "eden-tools: request failed (${status_code})" >&2
  eden_pretty_json_file "$response_file" 0 >&2
  exit 1
}

eden_curl_json() {
  local method="$1"
  local request_path="$2"
  local body_file="${3:-}"
  local response_file="$4"
  local url

  if [[ "$request_path" == http://* || "$request_path" == https://* ]]; then
    url="$request_path"
  else
    url="$(eden_api_url)${request_path}"
  fi

  local -a command=(
    curl
    -sS
    -X "$method"
    "$url"
    -H "accept: application/json"
    -H "x-api-key: $(eden_api_key)"
    -H "Authorization: Bearer $(eden_api_key)"
    -o "$response_file"
    -w "%{http_code}"
  )

  if [[ -n "$body_file" ]]; then
    command+=(
      -H "content-type: application/json"
      --data-binary "@$body_file"
    )
  fi

  "${command[@]}"
}

eden_write_wrapped_body() {
  local raw_input_file="$1"
  local wrapped_body_file="$2"
  node - "$raw_input_file" "$wrapped_body_file" <<'NODE'
const fs = require("fs");
const [rawInputFile, wrappedBodyFile] = process.argv.slice(2);
const raw = fs.readFileSync(rawInputFile, "utf8").trim();
const parsed = raw === "" ? {} : JSON.parse(raw);
fs.writeFileSync(wrappedBodyFile, JSON.stringify({ data: parsed }));
NODE
}

eden_print_result_file() {
  local file_path="$1"
  local compact="${2:-0}"
  node - "$file_path" "$compact" <<'NODE'
const fs = require("fs");
const [filePath, compact] = process.argv.slice(2);
const payload = JSON.parse(fs.readFileSync(filePath, "utf8"));

function unwrap(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return value;
  }
  if (value.output !== undefined) {
    return value.output;
  }
  if (value.result !== undefined) {
    return value.result;
  }
  return value;
}

const rendered = unwrap(payload);
process.stdout.write(JSON.stringify(rendered, null, compact === "1" ? 0 : 2));
process.stdout.write("\n");
NODE
}
