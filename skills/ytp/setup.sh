#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SKILL_DIR/../.." && pwd)"
UV_CACHE_DIR="$ROOT_DIR/.uv-cache"
OUTPUT_DIR="$ROOT_DIR/outputs/ytp"
PYTHON_BIN="$SKILL_DIR/.venv/bin/python"

if ! command -v uv >/dev/null 2>&1; then
  echo "ytp: uv is required but was not found on PATH" >&2
  exit 1
fi

mkdir -p "$UV_CACHE_DIR" "$OUTPUT_DIR"

if [[ ! -x "$PYTHON_BIN" ]]; then
  UV_CACHE_DIR="$UV_CACHE_DIR" uv venv "$SKILL_DIR/.venv"
fi

if ! "$PYTHON_BIN" -c "import imageio_ffmpeg, numpy, PIL" >/dev/null 2>&1; then
  UV_CACHE_DIR="$UV_CACHE_DIR" uv pip install --python "$PYTHON_BIN" -r "$SKILL_DIR/requirements.txt"
fi

"$SKILL_DIR/scripts/ffmpeg" -version >/dev/null

echo "ytp: ready"
echo "$OUTPUT_DIR"
