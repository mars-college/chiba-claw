#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";

const configPath = process.argv[2];

if (!configPath) {
  throw new Error("config_path_required");
}

const env = process.env;
const raw = fs.existsSync(configPath) ? fs.readFileSync(configPath, "utf8").trim() : "";
const config = raw ? JSON.parse(raw) : {};

const ensureRecord = (parent, key) => {
  const value = parent[key];
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    parent[key] = {};
  }
  return parent[key];
};

const parseCsv = (value) =>
  typeof value === "string" && value.trim() !== ""
    ? value
        .split(",")
        .map((entry) => entry.trim())
        .filter(Boolean)
    : [];

const workspaceDir = path.resolve(env.OPENCLAW_WORKSPACE_DIR || process.cwd());
const agents = ensureRecord(config, "agents");
const agentDefaults = ensureRecord(agents, "defaults");
agentDefaults.workspace = workspaceDir;

const skills = ensureRecord(config, "skills");
const load = ensureRecord(skills, "load");
load.watch = true;
load.watchDebounceMs = Number(env.OPENCLAW_SKILL_WATCH_DEBOUNCE_MS || 250);

const gateway = ensureRecord(config, "gateway");
gateway.mode = env.OPENCLAW_GATEWAY_MODE || gateway.mode || "local";
gateway.bind = env.OPENCLAW_GATEWAY_BIND || gateway.bind || "loopback";

const gatewayPort = Number(env.OPENCLAW_GATEWAY_PORT || gateway.port || 19789);
if (!Number.isInteger(gatewayPort) || gatewayPort <= 0) {
  throw new Error("invalid_openclaw_gateway_port");
}
gateway.port = gatewayPort;

const gatewayAuth = ensureRecord(gateway, "auth");
gatewayAuth.mode = env.OPENCLAW_GATEWAY_AUTH_MODE || gatewayAuth.mode || "token";
if (typeof env.OPENCLAW_GATEWAY_TOKEN === "string" && env.OPENCLAW_GATEWAY_TOKEN.trim() !== "") {
  gatewayAuth.token = env.OPENCLAW_GATEWAY_TOKEN.trim();
}

if (env.OPENCLAW_ENABLE_DISCORD !== "0" && env.OPENCLAW_ENABLE_DISCORD?.toLowerCase() !== "false") {
  const token = env.DISCORD_BOT_TOKEN?.trim();
  if (!token) {
    throw new Error("discord_bot_token_required");
  }

  const channels = ensureRecord(config, "channels");
  const discord = ensureRecord(channels, "discord");
  discord.enabled = true;
  discord.token = token;
  discord.groupPolicy = env.DISCORD_GROUP_POLICY || discord.groupPolicy || "allowlist";
  discord.streaming = env.DISCORD_STREAMING || discord.streaming || "off";
  discord.dmPolicy = env.DISCORD_DM_POLICY || discord.dmPolicy || "pairing";
  const inboundWorker = ensureRecord(discord, "inboundWorker");
  const inboundWorkerTimeoutMs = Number(
    env.OPENCLAW_DISCORD_INBOUND_WORKER_TIMEOUT_MS ||
      env.DISCORD_INBOUND_WORKER_TIMEOUT_MS ||
      inboundWorker.runTimeoutMs ||
      600000,
  );
  if (!Number.isInteger(inboundWorkerTimeoutMs) || inboundWorkerTimeoutMs <= 0) {
    throw new Error("invalid_discord_inbound_worker_timeout_ms");
  }
  inboundWorker.runTimeoutMs = inboundWorkerTimeoutMs;

  const allowFrom = parseCsv(env.DISCORD_ALLOW_FROM);
  if (allowFrom.length > 0) {
    discord.allowFrom = allowFrom;
  }

  const guilds = ensureRecord(discord, "guilds");
  for (const guildId of parseCsv(env.DISCORD_ALLOWED_GUILD_IDS)) {
    guilds[guildId] =
      guilds[guildId] && typeof guilds[guildId] === "object" && !Array.isArray(guilds[guildId])
        ? guilds[guildId]
        : {};
  }

  const channelIds = parseCsv(env.DISCORD_ALLOWED_CHANNEL_IDS);
  if (channelIds.length > 0) {
    const wildcard =
      guilds["*"] && typeof guilds["*"] === "object" && !Array.isArray(guilds["*"]) ? guilds["*"] : {};
    const channelsRecord =
      wildcard.channels && typeof wildcard.channels === "object" && !Array.isArray(wildcard.channels)
        ? wildcard.channels
        : {};
    for (const channelId of channelIds) {
      channelsRecord[channelId] = { allow: true };
    }
    wildcard.channels = channelsRecord;
    guilds["*"] = wildcard;
  }
}

fs.mkdirSync(path.dirname(configPath), { recursive: true });
fs.writeFileSync(configPath, `${JSON.stringify(config, null, 2)}\n`);
