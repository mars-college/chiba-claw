#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ ! -f "$ROOT_DIR/.env" ]]; then
  echo "missing $ROOT_DIR/.env" >&2
  echo "copy .env.example to .env and fill in the values first" >&2
  exit 1
fi

# shellcheck disable=SC1091
source "$ROOT_DIR/scripts/load-env.sh" "$ROOT_DIR/.env"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "missing required command: $1" >&2
    exit 1
  fi
}

require_cmd openclaw
require_cmd node
require_cmd bash

normalize_bool() {
  printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]'
}

is_enabled() {
  case "$(normalize_bool "${1:-}")" in
    "" | 1 | true | yes | on)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

if [[ -z "${OPENCLAW_GATEWAY_TOKEN:-}" ]]; then
  echo "OPENCLAW_GATEWAY_TOKEN is required" >&2
  exit 1
fi

if is_enabled "${OPENCLAW_ENABLE_DISCORD:-1}" && [[ -z "${DISCORD_BOT_TOKEN:-}" ]]; then
  echo "DISCORD_BOT_TOKEN is required when OPENCLAW_ENABLE_DISCORD is enabled" >&2
  exit 1
fi

PROFILE="$OPENCLAW_PROFILE"
WORKSPACE_DIR="$(cd "$OPENCLAW_WORKSPACE_DIR" && pwd)"
AGENT_ID="$OPENCLAW_AGENT_ID"
AGENT_NAME="$OPENCLAW_AGENT_NAME"

openclaw --profile "$PROFILE" onboard \
  --non-interactive \
  --accept-risk \
  --skip-channels \
  --skip-health \
  --skip-ui \
  --skip-search \
  --skip-daemon \
  --skip-skills \
  --workspace "$WORKSPACE_DIR"

CONFIG_PATH="$(openclaw --profile "$PROFILE" config file | tail -n 1)"
CONFIG_PATH="${CONFIG_PATH/#\~/$HOME}"
node "$ROOT_DIR/scripts/configure-openclaw-profile.mjs" "$CONFIG_PATH"

openclaw --profile "$PROFILE" config validate
openclaw --profile "$PROFILE" doctor --fix --non-interactive --yes --no-workspace-suggestions

if ! node -e '
const fs = require("node:fs");
const file = process.argv[1];
const agentId = process.argv[2];
const raw = fs.existsSync(file) ? fs.readFileSync(file, "utf8").trim() : "";
const config = raw ? JSON.parse(raw) : {};
const agents = Array.isArray(config.agents?.list) ? config.agents.list : [];
process.exit(agents.some((row) => row && row.id === agentId) ? 0 : 1);
' "$CONFIG_PATH" "$AGENT_ID"; then
  AGENT_ADD_ARGS=(--profile "$PROFILE" agents add "$AGENT_ID" --non-interactive --workspace "$WORKSPACE_DIR")
  if [[ -n "${OPENCLAW_AGENT_MODEL:-}" ]]; then
    AGENT_ADD_ARGS+=(--model "$OPENCLAW_AGENT_MODEL")
  fi
  openclaw "${AGENT_ADD_ARGS[@]}"
fi

IDENTITY_ARGS=(--profile "$PROFILE" agents set-identity --agent "$AGENT_ID" --name "$AGENT_NAME")
if [[ -n "${OPENCLAW_AGENT_EMOJI:-}" ]]; then
  IDENTITY_ARGS+=(--emoji "$OPENCLAW_AGENT_EMOJI")
fi
if [[ -n "${OPENCLAW_AGENT_AVATAR:-}" ]]; then
  IDENTITY_ARGS+=(--avatar "$OPENCLAW_AGENT_AVATAR")
fi
openclaw "${IDENTITY_ARGS[@]}"

node "$ROOT_DIR/scripts/configure-openclaw-agent.mjs" "$CONFIG_PATH" "$AGENT_ID"

if is_enabled "${OPENCLAW_ENABLE_DISCORD:-1}"; then
  openclaw --profile "$PROFILE" agents bind --agent "$AGENT_ID" --bind discord
fi

bash "$ROOT_DIR/scripts/setup-skills.sh"

if is_enabled "${OPENCLAW_INSTALL_GATEWAY_SERVICE:-0}"; then
  openclaw --profile "$PROFILE" gateway install --force --runtime "$OPENCLAW_GATEWAY_RUNTIME"
fi

if is_enabled "${OPENCLAW_START_GATEWAY_SERVICE:-0}"; then
  openclaw --profile "$PROFILE" gateway start
fi

echo "chibaclaw: installed"
echo "profile=$PROFILE"
echo "workspace=$WORKSPACE_DIR"
echo "agent=$AGENT_ID"
