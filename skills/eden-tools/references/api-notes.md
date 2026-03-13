# Eden Tool API Notes

These notes are derived from the sibling Eden2 repo at `../eden2`.

Run `bash skills/eden-tools/setup.sh` to generate `outputs/eden-tools/api-notes.local.md`
with resolved absolute source paths from `EDEN_SOURCE_REPO` or the default sibling repo.

## Routes

- Execute route for flat ids: `POST /v1/tools/:id/execute`
- Execute route for slash ids: `POST /v1/tools/:provider/:product/execute`
- Tool list route: `GET /v1/tools`
- Task poll route: `GET /v1/tasks/:id`

## Payloads

- Execute requests send `{"data": <tool input>}`.
- The execute route proxies into the Mastra runtime and returns the proxied tool response directly.
- The wrapper should therefore support both:
  - Immediate final tool results
  - Task-like payloads that need polling

## Auth

- Protected `/v1` routes accept agent-scoped API key auth.
- This wrapper sends both `x-api-key` and `Authorization: Bearer ...`.
- The dual-header approach is needed because the current execute proxy forwards `Authorization` to nested Mastra routes but does not forward `x-api-key`.

## Source Files

- `../eden2/apps/api/src/routes/tools.ts`
- `../eden2/apps/api/src/routes/tasks.ts`
- `../eden2/packages/sdk-ts/src/generated/openapi.ts`
