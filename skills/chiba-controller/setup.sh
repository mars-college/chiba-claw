#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SKILL_DIR/../.." && pwd)"

if [[ -f "$ROOT_DIR/scripts/load-env.sh" ]]; then
  # shellcheck source=scripts/load-env.sh
  source "$ROOT_DIR/scripts/load-env.sh" "$ROOT_DIR/.env"
fi

CONTROLLER_REPO="${CHIBA_CONTROLLER_REPO:-$ROOT_DIR/../chiba-controller}"
CONTROL_API_URL="${CHIBA_API_URL:-${CHIBA_CONTROLLER_API_URL:-${CHIBA3_CONTROL_API_URL:-}}}"
CONTROL_API_URL="${CONTROL_API_URL%/}"

if ! command -v node >/dev/null 2>&1; then
  echo "chiba-controller: node is required" >&2
  exit 1
fi

if ! command -v pnpm >/dev/null 2>&1; then
  echo "chiba-controller: pnpm is required" >&2
  exit 1
fi

if [[ ! -d "$CONTROLLER_REPO/apps/control-mcp" ]]; then
  echo "chiba-controller: missing control-mcp app under $CONTROLLER_REPO" >&2
  exit 1
fi

if [[ -z "$CONTROL_API_URL" ]]; then
  echo "chiba-controller: set CHIBA_API_URL (preferred), CHIBA_CONTROLLER_API_URL, or CHIBA3_CONTROL_API_URL in the environment or repo .env" >&2
  exit 1
fi

curl -fsS "$CONTROL_API_URL/api/v1/resources/snapshot" >/dev/null

echo "chiba-controller: ready"
echo "control_api=$CONTROL_API_URL"
echo "controller_repo=$CONTROLLER_REPO"
