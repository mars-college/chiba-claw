---
name: chiba-controller
description: Use the configured Chiba controller API plus the local chiba-controller MCP/API surfaces to upload media, send targets to screens, query screen status, search the media library, and create playlists, blocks, channels, and profiles.
---

# Chiba Controller

Use this skill when the user wants to manipulate the live Chiba controller stack on the local network.

## Inputs

The scripts auto-load the repo `.env` when present. Configure:

- `CHIBA_CONTROLLER_HOST`
- `CHIBA_API_URL` (preferred)
- `CHIBA_CONTROLLER_API_URL`
- `CHIBA3_CONTROL_API_URL`
- Optional `CHIBA_CONTROLLER_REPO` to override the default sibling repo at `../chiba-controller`

`CHIBA_CONTROLLER_HOST` is optional if `CHIBA_API_URL` already points at the control API.

## Setup

Run:

```bash
bash skills/chiba-controller/setup.sh
```

This checks the live control API and the local `control-mcp` app.

## Preferred workflow

Use the existing MCP-backed helpers for read/search/upload flows:

- `node skills/chiba-controller/scripts/search-media.mjs --query "term"`
- `node skills/chiba-controller/scripts/query-nodes.mjs --query west --include-runtime`
- `node skills/chiba-controller/scripts/screen-state.mjs --screen-id lower-west-2`
- `node skills/chiba-controller/scripts/upload-media.mjs --path /abs/file.mp4 --artist jmill`
- `node skills/chiba-controller/scripts/send-media.mjs --media-id m-upload-123 --screen-id lower-west-2 --dry-run`
- `node skills/chiba-controller/scripts/upload-and-send.mjs --path /abs/file.mp4 --screen-id lower-west-2 --dry-run-send`

Use the direct control API for apply operations and resource upserts:

- `node skills/chiba-controller/scripts/send-target.mjs --target-kind media --target-id m-upload-123 --screen-id lower-west-2 --dry-run`
- `node skills/chiba-controller/scripts/upsert-resource.mjs --kind playlist --input /abs/playlist.json`

## Notes

- `upload-and-send` polls the upload job by default and then sends the resulting media or playlist target.
- Prefer `--dry-run` or `--dry-run-send` unless the user clearly wants a live screen change.
- For exact screen assignment state across the fleet, use both:
  - `query-nodes.mjs` for connectivity/runtime status
  - `screen-assignments.mjs` or `screen-state.mjs` for desired assignment state
- Resource creation uses full-snapshot upserts under the hood: fetch snapshot, replace or append the specified resource by id, then POST the merged snapshot back.
- For resource JSON shapes, load `references/resource-examples.md`.
