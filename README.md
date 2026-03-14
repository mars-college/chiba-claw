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

## Docker Compose Gateway

If you want the OpenClaw gateway itself containerized on a local Ubuntu or Debian server, this repo includes a Docker Compose flow that mounts this repo as the workspace and persists the OpenClaw home dir on the host.

What it does:

- builds `Dockerfile.openclaw` on top of `ghcr.io/openclaw/openclaw:latest`
- adds the missing local toolchain this workspace expects inside Docker:
  `uv`, `python3 -m pip`, and `ffmpeg`
- mounts this repo into the container as the OpenClaw workspace
- persists OpenClaw state under `OPENCLAW_DOCKER_STATE_DIR` (default: `$HOME/.openclaw`)
- writes a generated `.openclaw-docker.env` with container-safe overrides
- bootstraps the profile and agent inside a one-shot CLI container
- starts the gateway as a long-running Compose service
- skips `scripts/setup-skills.sh` by default inside Docker so missing sibling repos and extra toolchains do not block the gateway bootstrap

Bring it up:

```bash
bash scripts/openclaw-docker.sh up
```

Useful follow-ups:

```bash
bash scripts/openclaw-docker.sh build
bash scripts/openclaw-docker.sh logs
bash scripts/openclaw-docker.sh ps
bash scripts/openclaw-docker.sh down
```

The Docker image now includes the runtime pieces the repo's skill installers assume are present:

- upstream OpenClaw image: `openclaw`, `node`, `npm`, `pnpm`, `python3`, `curl`, `git`
- repo Dockerfile additions: `uv`, `python3 -m pip`, `python3 -m venv`, `ffmpeg`

The default Docker path still keeps `OPENCLAW_SKIP_SKILL_SETUP=1`, because some skills also assume sibling repos such as `../chiba-controller` and `../eden2` are available. If you mount or colocate those repos on the server and want the container bootstrap to run `scripts/setup-skills.sh`, set `OPENCLAW_SKIP_SKILL_SETUP=0` in `.env`.

To access the Control UI from your laptop, tunnel the gateway port over SSH:

```bash
ssh -N -L 19789:127.0.0.1:19789 <user>@<server>
```

If you change `OPENCLAW_GATEWAY_PORT`, use that port in the tunnel command instead.

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
