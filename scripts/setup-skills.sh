#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CACHE_DIR="$ROOT_DIR/.npm-cache"
ENV_FILE="${OPENCLAW_ENV_FILE:-$ROOT_DIR/.env}"

# shellcheck disable=SC1091
source "$ROOT_DIR/scripts/load-env.sh" "$ENV_FILE"

mkdir -p "$CACHE_DIR"

shopt -s nullglob
for skill_dir in "$ROOT_DIR"/skills/*; do
  [[ -d "$skill_dir" ]] || continue

  if [[ -x "$skill_dir/setup.sh" ]]; then
    echo "Running setup for $(basename "$skill_dir")"
    "$skill_dir/setup.sh"
    continue
  fi

  if [[ -f "$skill_dir/package.json" ]]; then
    echo "Installing Node dependencies for $(basename "$skill_dir")"
    if [[ -f "$skill_dir/package-lock.json" ]]; then
      npm ci --prefix "$skill_dir" --cache "$CACHE_DIR"
    else
      npm install --prefix "$skill_dir" --cache "$CACHE_DIR"
    fi
  fi

  if [[ -f "$skill_dir/requirements.txt" ]]; then
    echo "Installing Python dependencies for $(basename "$skill_dir")"
    python3 -m pip install -r "$skill_dir/requirements.txt"
  fi
done
