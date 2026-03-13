# Chiba Claw

Chiba Claw is an OpenClaw workspace with a small set of local skills for:

- Chiba controller operations
- Eden API tool execution
- Mars lore sync and search
- Remotion video generation
- YTP-style video generation

The repo is designed to be installed as an OpenClaw workspace and agent, with a default assumption that related repos live next to it as sibling directories.

## Layout Assumptions

By default, the workspace resolves related local repos like this:

- `../chiba-controller`
- `../eden2`

That means a typical layout looks like:

```text
parent/
  chiba-claw/
  chiba-controller/
  eden2/
```

If your repos live somewhere else, override the defaults in `.env`:

- `CHIBA_CONTROLLER_REPO`
- `EDEN_SOURCE_REPO`

Relative override values are resolved from the `chiba-claw` repo root.

## Prerequisites

Required for the main install:

- `openclaw`
- `bash`
- `node` 20+

Needed by specific skills:

- `curl` for `eden-tools` and controller setup probes
- `npm` for `remotion` and Node-based skill installs
- `pnpm` for `chiba-controller`
- `uv` for `remotion` and `ytp`

Service credentials and endpoints are optional unless you want those skills live:

- `DISCORD_BOT_TOKEN` if Discord is enabled
- `CHIBA_API_URL` for controller API access
- `EDEN_API_URL` and `EDEN_API_KEY` for Eden tool execution
- `LOREBOOK_URL` or `MARS_LORE_SHEET_URL` for Mars lore sync

## Install

1. Clone the workspace.
2. If you use the related local repos, place them as siblings to this repo or plan to override their paths in `.env`.
3. Copy the example env file:

```bash
cp .env.example .env
```

4. Edit `.env`.

Minimum fields to set for a normal OpenClaw install:

- `OPENCLAW_GATEWAY_TOKEN`
- `DISCORD_BOT_TOKEN` if `OPENCLAW_ENABLE_DISCORD=1`

Common fields you should review:

- `OPENCLAW_WORKSPACE_DIR`
- `OPENCLAW_PROFILE`
- `OPENCLAW_AGENT_ID`
- `OPENCLAW_AGENT_NAME`
- `OPENCLAW_GATEWAY_PORT`
- `CHIBA_API_URL`
- `CHIBA_CONTROLLER_REPO`
- `EDEN_API_URL`
- `EDEN_API_KEY`
- `EDEN_SOURCE_REPO`

5. Run the installer:

```bash
bash scripts/install-openclaw-workspace.sh
```

What the installer does:

- validates required env
- onboards the OpenClaw profile non-interactively
- configures the profile and agent
- binds Discord if enabled
- runs skill setup
- optionally installs and starts the OpenClaw gateway service

## Skills Only

If you do not want the full OpenClaw workspace install and only want local skill dependencies and setup:

```bash
bash scripts/setup-skills.sh
```

This runs each skill's setup script or dependency install.

## Verify

Run the test suite:

```bash
bash scripts/test-skills.sh
```

You can also run setup for an individual skill:

```bash
bash skills/eden-tools/setup.sh
bash skills/chiba-controller/setup.sh
bash skills/remotion/setup.sh
bash skills/ytp/setup.sh
```

## Notes

- `skills/eden-tools/setup.sh` generates `outputs/eden-tools/api-notes.local.md` with resolved absolute local source paths for the sibling `eden2` repo.
- `CHIBA_CONTROLLER_REPO` and `EDEN_SOURCE_REPO` default to sibling repos and are resolved to absolute paths during setup.
- If a skill is not fully configured, setup should still leave the repo in a usable state and print what is missing.

## Outputs

Generated artifacts land under `outputs/`, including:

- `outputs/eden-tools/`
- `outputs/mars-lore/`
- `outputs/remotion/`
- `outputs/ytp/`
