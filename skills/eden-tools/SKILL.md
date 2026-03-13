---
name: eden-tools
description: Use EDEN_API_URL plus an agent-scoped EDEN_API_KEY to list and execute Eden API tools through /v1/tools/.../execute, automatically polling /v1/tasks/{id} when a tool returns an async task-like response.
---

# Eden Tools

Use this skill when the user wants to call Eden API tools directly with an API key instead of going through chat.

## Inputs

- `EDEN_API_URL`
- `EDEN_API_KEY`
- Optional `EDEN_SOURCE_REPO` to override the default sibling repo at `../eden2`
- Optional `EDEN_POLL_INTERVAL_SECONDS`
- Optional `EDEN_TOOL_TIMEOUT_SECONDS`

The scripts auto-load the repo `.env` when present.

## Workflow

1. Run `bash skills/eden-tools/setup.sh`
   This generates `outputs/eden-tools/api-notes.local.md` with resolved absolute source paths from `EDEN_SOURCE_REPO` or the default sibling `../eden2`.
2. Discover tool ids with `bash skills/eden-tools/scripts/list-tools.sh --limit 100`
3. Execute with repeated args first, for example:
   `bash skills/eden-tools/scripts/execute-tool.sh --tool-id fal/nano-banana --arg prompt="banana dj" --arg num_images=2`
4. Use `--data '{"...": ...}'` or `--data-file /abs/input.json` only when the payload is too awkward to express as repeated args.
5. The wrapper sends `{ "data": ... }` to the Eden execute route. If the response already looks final, it prints it. If the response looks like a task or exposes a poll URL, it waits until terminal status and prints the terminal output.
6. The wrapper sends both `x-api-key` and `Authorization: Bearer ...` so auth survives current Eden execute proxy behavior.

## Notes

- For slash tool ids such as `fal/nano-banana`, the wrapper uses Eden's compound execute route: `/v1/tools/:provider/:product/execute`.
- `--arg key=value` tries `JSON.parse` on the value first, so `2`, `true`, `null`, arrays, and objects keep their JSON types; otherwise the value stays a string.
- Successful terminal task payloads are unwrapped to `output` or `result` when present; otherwise the full terminal object is printed.
- Use `--no-wait` if you want the raw execute response without polling.
- For generic route behavior, read `references/api-notes.md`.
- For resolved local absolute source paths after setup, read `outputs/eden-tools/api-notes.local.md`.
