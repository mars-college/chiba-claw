#!/usr/bin/env node

import fs from "node:fs";

const configPath = process.argv[2];
const agentId = process.argv[3] || process.env.OPENCLAW_AGENT_ID || "chibaclaw";

if (!configPath) {
  throw new Error("config_path_required");
}

const defaultSkills = [
  "1password",
  "github",
  "weather",
  "tmux",
  "video-frames",
  "healthcheck",
  "session-logs",
  "skill-creator",
  "coding-agent",
  "mars-lore-search",
  "mars-lore-update",
  "remotion",
  "ytp",
  "chiba-controller",
  "eden-tools",
];

const fromEnv =
  typeof process.env.OPENCLAW_AGENT_SKILLS === "string" && process.env.OPENCLAW_AGENT_SKILLS.trim() !== ""
    ? process.env.OPENCLAW_AGENT_SKILLS.split(",")
        .map((entry) => entry.trim())
        .filter(Boolean)
    : null;

const allowedSkills = fromEnv ?? defaultSkills;
const raw = fs.existsSync(configPath) ? fs.readFileSync(configPath, "utf8").trim() : "";
const config = raw ? JSON.parse(raw) : {};

if (!Array.isArray(config.agents?.list)) {
  throw new Error("agents_list_missing");
}

const agent = config.agents.list.find((entry) => entry && entry.id === agentId);
if (!agent) {
  throw new Error(`agent_not_found:${agentId}`);
}

agent.skills = allowedSkills;

fs.writeFileSync(configPath, `${JSON.stringify(config, null, 2)}\n`);
