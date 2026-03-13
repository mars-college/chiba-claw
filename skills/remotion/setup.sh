#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SKILL_DIR/../.." && pwd)"
CACHE_DIR="$ROOT_DIR/.npm-cache"
UV_CACHE_DIR="$ROOT_DIR/.uv-cache"
OUTPUT_DIR="$ROOT_DIR/outputs/remotion"
PYTHON_BIN="$SKILL_DIR/.venv/bin/python"

if ! command -v npm >/dev/null 2>&1; then
  echo "remotion: npm is required but was not found on PATH" >&2
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "remotion: uv is required but was not found on PATH" >&2
  exit 1
fi

mkdir -p "$CACHE_DIR" "$UV_CACHE_DIR" "$OUTPUT_DIR"

if [[ ! -x "$PYTHON_BIN" ]]; then
  UV_CACHE_DIR="$UV_CACHE_DIR" uv venv "$SKILL_DIR/.venv"
fi

if ! "$PYTHON_BIN" -c "import imageio_ffmpeg, PIL" >/dev/null 2>&1; then
  UV_CACHE_DIR="$UV_CACHE_DIR" uv pip install --python "$PYTHON_BIN" -r "$SKILL_DIR/requirements.txt"
fi

if [[ ! -x "$SKILL_DIR/node_modules/.bin/remotion" ]]; then
  if [[ -f "$SKILL_DIR/package-lock.json" ]]; then
    npm ci --prefix "$SKILL_DIR" --cache "$CACHE_DIR"
  else
    npm install --prefix "$SKILL_DIR" --cache "$CACHE_DIR"
  fi
fi

if [[ ! -x "$SKILL_DIR/node_modules/.bin/remotion" ]]; then
  echo "remotion: CLI install did not produce node_modules/.bin/remotion" >&2
  exit 1
fi

"$SKILL_DIR/scripts/ffmpeg" -version >/dev/null

echo "remotion: ready"
echo "$OUTPUT_DIR"
