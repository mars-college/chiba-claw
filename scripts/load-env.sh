#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${1:-$ROOT_DIR/.env}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

resolve_local_repo_path() {
  local raw_path="$1"
  if [[ -z "$raw_path" ]]; then
    return 1
  fi

  if [[ "$raw_path" != /* ]]; then
    raw_path="$ROOT_DIR/$raw_path"
  fi

  local parent_dir
  local base_name
  local parent_abs

  parent_dir="$(dirname "$raw_path")"
  base_name="$(basename "$raw_path")"

  if parent_abs="$(cd "$parent_dir" 2>/dev/null && pwd -P)"; then
    printf "%s/%s\n" "$parent_abs" "$base_name"
    return 0
  fi

  printf "%s\n" "$raw_path"
}

export EDEN_SOURCE_REPO="$(resolve_local_repo_path "${EDEN_SOURCE_REPO:-$ROOT_DIR/../eden2}")"
export CHIBA_CONTROLLER_REPO="$(resolve_local_repo_path "${CHIBA_CONTROLLER_REPO:-$ROOT_DIR/../chiba-controller}")"

if [[ -n "${LOREBOOK_URL:-}" && -z "${MARS_LORE_SHEET_URL:-}" ]]; then
  export MARS_LORE_SHEET_URL="$LOREBOOK_URL"
fi

export MARS_LORE_OUTPUT_DIR="${MARS_LORE_OUTPUT_DIR:-outputs/mars-lore}"

if [[ -n "${CHIBA_API_URL:-}" ]]; then
  export CHIBA_CONTROLLER_API_URL="${CHIBA_CONTROLLER_API_URL:-$CHIBA_API_URL}"
  export CHIBA3_CONTROL_API_URL="${CHIBA3_CONTROL_API_URL:-$CHIBA_API_URL}"
  if [[ -z "${CHIBA_CONTROLLER_HOST:-}" ]]; then
    export CHIBA_CONTROLLER_HOST="$(printf '%s\n' "$CHIBA_API_URL" | sed -E 's#^(https?://[^/]+).*$#\1#')"
  fi
fi

export OPENCLAW_PROFILE="${OPENCLAW_PROFILE:-chibaclaw}"
export OPENCLAW_WORKSPACE_DIR="$(resolve_local_repo_path "${OPENCLAW_WORKSPACE_DIR:-$ROOT_DIR}")"
export OPENCLAW_AGENT_ID="${OPENCLAW_AGENT_ID:-chibaclaw}"
export OPENCLAW_AGENT_NAME="${OPENCLAW_AGENT_NAME:-ChibaClaw}"
export OPENCLAW_GATEWAY_PORT="${OPENCLAW_GATEWAY_PORT:-19789}"
export OPENCLAW_GATEWAY_BIND="${OPENCLAW_GATEWAY_BIND:-loopback}"
export OPENCLAW_GATEWAY_RUNTIME="${OPENCLAW_GATEWAY_RUNTIME:-node}"
export OPENCLAW_INSTALL_GATEWAY_SERVICE="${OPENCLAW_INSTALL_GATEWAY_SERVICE:-0}"
export OPENCLAW_START_GATEWAY_SERVICE="${OPENCLAW_START_GATEWAY_SERVICE:-0}"
export OPENCLAW_ENABLE_DISCORD="${OPENCLAW_ENABLE_DISCORD:-1}"
export OPENCLAW_DISCORD_INBOUND_WORKER_TIMEOUT_MS="${OPENCLAW_DISCORD_INBOUND_WORKER_TIMEOUT_MS:-600000}"
export DISCORD_GROUP_POLICY="${DISCORD_GROUP_POLICY:-allowlist}"
export DISCORD_DM_POLICY="${DISCORD_DM_POLICY:-pairing}"
