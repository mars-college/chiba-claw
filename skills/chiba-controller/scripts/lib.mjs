#!/usr/bin/env node

import { readFileSync } from "node:fs";
import fs from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

export const DEFAULT_NAMESPACE = "prod";
export const DEFAULT_REGISTRY_ID = "prod";
export const DEFAULT_CONTROLLER_ID = "chiba-claw";
const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDir, "../../..");
export const DEFAULT_CONTROLLER_REPO = path.resolve(repoRoot, "..", "chiba-controller");

function normalizeValue(value) {
  return String(value ?? "").trim();
}

function parseDotEnv(contents) {
  const entries = {};

  for (const rawLine of contents.split(/\r?\n/u)) {
    const line = rawLine.trim();
    if (line === "" || line.startsWith("#")) {
      continue;
    }

    const match = rawLine.match(/^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$/u);
    if (!match) {
      continue;
    }

    const [, key] = match;
    let [, , value] = match;
    value = value.trim();

    if (
      (value.startsWith(`"`) && value.endsWith(`"`)) ||
      (value.startsWith(`'`) && value.endsWith(`'`))
    ) {
      const quote = value[0];
      value = value.slice(1, -1);
      if (quote === `"`) {
        value = value
          .replace(/\\n/g, "\n")
          .replace(/\\r/g, "\r")
          .replace(/\\"/g, `"`)
          .replace(/\\\\/g, "\\");
      }
    } else {
      value = value.replace(/\s+#.*$/u, "").trim();
    }

    entries[key] = value;
  }

  return entries;
}

function setIfMissing(key, value) {
  if (value == null || value === "" || normalizeValue(process.env[key]) !== "") {
    return;
  }

  process.env[key] = value;
}

export function loadRepoEnvironment(
  envFile = process.env.CHIBA_CLAW_ENV_FILE || path.join(repoRoot, ".env")
) {
  try {
    const contents = readFileSync(envFile, "utf8");
    const entries = parseDotEnv(contents);

    for (const [key, value] of Object.entries(entries)) {
      setIfMissing(key, value);
    }
  } catch (error) {
    if (error && typeof error === "object" && "code" in error && error.code === "ENOENT") {
      return false;
    }
    throw error;
  }

  const apiUrl =
    normalizeValue(process.env.CHIBA_API_URL) ||
    normalizeValue(process.env.CHIBA_CONTROLLER_API_URL) ||
    normalizeValue(process.env.CHIBA3_CONTROL_API_URL);

  if (apiUrl !== "") {
    setIfMissing("CHIBA_API_URL", apiUrl);
    setIfMissing("CHIBA_CONTROLLER_API_URL", apiUrl);
    setIfMissing("CHIBA3_CONTROL_API_URL", apiUrl);

    try {
      setIfMissing("CHIBA_CONTROLLER_HOST", new URL(apiUrl).origin);
    } catch {
      // Ignore malformed configured URLs here; the caller gets a clearer error later.
    }
  }

  return true;
}

function configuredControlApiUrl() {
  return (
    normalizeValue(process.env.CHIBA_API_URL) ||
    normalizeValue(process.env.CHIBA_CONTROLLER_API_URL) ||
    normalizeValue(process.env.CHIBA3_CONTROL_API_URL)
  );
}

function resolveRepoPath(value, fallback) {
  const configured = normalizeValue(value) || normalizeValue(fallback);
  if (configured === "") {
    return "";
  }
  return path.isAbsolute(configured) ? path.normalize(configured) : path.resolve(repoRoot, configured);
}

export function controllerRepo() {
  return resolveRepoPath(process.env.CHIBA_CONTROLLER_REPO, DEFAULT_CONTROLLER_REPO);
}

export function controllerHost() {
  const hostOverride = normalizeValue(process.env.CHIBA_CONTROLLER_HOST);
  if (hostOverride !== "") {
    return hostOverride;
  }

  const apiUrl = configuredControlApiUrl();
  if (apiUrl) {
    try {
      return new URL(apiUrl).origin;
    } catch {
      throw new Error(
        "invalid_chiba_api_url: set CHIBA_API_URL (or CHIBA_CONTROLLER_API_URL / CHIBA3_CONTROL_API_URL) to a valid absolute URL"
      );
    }
  }

  throw new Error(
    "missing_chiba_controller_host: set CHIBA_API_URL or CHIBA_CONTROLLER_HOST in the environment or repo .env"
  );
}

export function controlApiUrl() {
  const apiUrl = configuredControlApiUrl();
  if (apiUrl === "") {
    throw new Error(
      "missing_chiba_api_url: set CHIBA_API_URL (preferred), CHIBA_CONTROLLER_API_URL, or CHIBA3_CONTROL_API_URL in the environment or repo .env"
    );
  }

  try {
    return new URL(apiUrl).toString();
  } catch {
    throw new Error(
      "invalid_chiba_api_url: set CHIBA_API_URL (or CHIBA_CONTROLLER_API_URL / CHIBA3_CONTROL_API_URL) to a valid absolute URL"
    );
  }
}

export function parseArgs(argv) {
  const flags = {};
  const positionals = [];

  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (!token.startsWith("--")) {
      positionals.push(token);
      continue;
    }

    const key = token.slice(2);
    const next = argv[index + 1];
    const value =
      next == null || next.startsWith("--")
        ? true
        : (index += 1, next);

    if (Object.hasOwn(flags, key)) {
      const current = flags[key];
      flags[key] = Array.isArray(current) ? current.concat(value) : [current, value];
      continue;
    }

    flags[key] = value;
  }

  return { flags, positionals };
}

export function readRequiredString(flags, key) {
  const value = flags[key];
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`missing_required_flag:${key}`);
  }
  return value.trim();
}

export function readOptionalString(flags, key) {
  const value = flags[key];
  return typeof value === "string" && value.trim() !== "" ? value.trim() : undefined;
}

export function readStringList(flags, key) {
  const value = flags[key];
  if (value == null) return [];
  const values = Array.isArray(value) ? value : [value];
  return values
    .flatMap((entry) =>
      String(entry)
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean)
    );
}

export function readBooleanFlag(flags, key, defaultValue = false) {
  const value = flags[key];
  if (value == null) return defaultValue;
  if (value === true) return true;
  const normalized = String(value).trim().toLowerCase();
  if (["1", "true", "yes", "on"].includes(normalized)) return true;
  if (["0", "false", "no", "off"].includes(normalized)) return false;
  throw new Error(`invalid_boolean_flag:${key}`);
}

export function readOptionalInteger(flags, key) {
  const value = flags[key];
  if (value == null) return undefined;
  const parsed = Number(value);
  if (!Number.isInteger(parsed)) {
    throw new Error(`invalid_integer_flag:${key}`);
  }
  return parsed;
}

export async function readJsonInput(flags) {
  if (typeof flags["input-json"] === "string") {
    return JSON.parse(flags["input-json"]);
  }

  if (typeof flags.input === "string") {
    const filePath = path.resolve(flags.input);
    return JSON.parse(await fs.readFile(filePath, "utf8"));
  }

  if (!process.stdin.isTTY) {
    const chunks = [];
    for await (const chunk of process.stdin) chunks.push(chunk);
    const raw = Buffer.concat(chunks).toString("utf8").trim();
    if (raw) return JSON.parse(raw);
  }

  throw new Error("json_input_required");
}

export async function fetchJson(apiPath, init = {}) {
  const url = new URL(apiPath, controlApiUrl());
  const response = await fetch(url, init);
  const raw = await response.text();
  const data = raw ? tryParseJson(raw) : null;
  if (!response.ok) {
    throw new Error(`http_${response.status}:${JSON.stringify(data ?? raw.slice(0, 240))}`);
  }
  return data;
}

export async function fetchSnapshot() {
  const payload = await fetchJson("/api/v1/resources/snapshot");
  return payload?.snapshot ?? payload;
}

export async function importResources(payload) {
  return fetchJson("/api/v1/resources/import", {
    method: "POST",
    headers: {
      "content-type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export async function applyTarget({
  targetKind,
  targetId,
  nodeIds,
  namespace = DEFAULT_NAMESPACE,
  registryId = DEFAULT_REGISTRY_ID,
  controllerId = DEFAULT_CONTROLLER_ID,
  dryRun = false,
  launch = {},
}) {
  const body = {
    target: targetKind,
    id: targetId,
    piIds: nodeIds,
    namespace,
    registryId,
    controllerId,
    dryRun,
    ...launch,
  };
  return fetchJson("/api/ops/apply-target", {
    method: "POST",
    headers: {
      "content-type": "application/json",
    },
    body: JSON.stringify(body),
  });
}

export async function listScreenAssignments({
  namespace = DEFAULT_NAMESPACE,
  screenId,
} = {}) {
  const params = new URLSearchParams();
  params.set("namespace", namespace);
  if (screenId) params.set("screenId", screenId);
  return fetchJson(`/api/v1/screen-assignments?${params.toString()}`);
}

export async function deleteResource(kind, id) {
  const pathByKind = {
    media: `/api/v1/resources/media/${encodeURIComponent(id)}`,
    playlist: `/api/v1/resources/playlists/${encodeURIComponent(id)}`,
    block: `/api/v1/resources/blocks/${encodeURIComponent(id)}`,
    channel: `/api/v1/resources/channels/${encodeURIComponent(id)}`,
    profile: `/api/v1/resources/profiles/${encodeURIComponent(id)}`,
  };
  const apiPath = pathByKind[kind];
  if (!apiPath) throw new Error(`unsupported_resource_kind:${kind}`);
  return fetchJson(apiPath, {
    method: "DELETE",
  });
}

function tryParseJson(raw) {
  try {
    return JSON.parse(raw);
  } catch {
    return { raw };
  }
}

function encodeMessage(payload) {
  const json = JSON.stringify(payload);
  return `Content-Length: ${Buffer.byteLength(json, "utf8")}\r\n\r\n${json}`;
}

function parseMessages(bufferState, chunk, onMessage) {
  bufferState.buffer = Buffer.concat([
    bufferState.buffer,
    Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk),
  ]);

  for (;;) {
    const headerEnd = bufferState.buffer.indexOf("\r\n\r\n");
    if (headerEnd < 0) return;
    const headerText = bufferState.buffer.slice(0, headerEnd).toString("utf8");
    const match = headerText.match(/content-length:\s*(\d+)/i);
    if (!match) {
      throw new Error("mcp_missing_content_length");
    }
    const length = Number(match[1]);
    const bodyStart = headerEnd + 4;
    const bodyEnd = bodyStart + length;
    if (bufferState.buffer.length < bodyEnd) return;
    const bodyText = bufferState.buffer.slice(bodyStart, bodyEnd).toString("utf8");
    bufferState.buffer = bufferState.buffer.slice(bodyEnd);
    onMessage(JSON.parse(bodyText));
  }
}

export async function callControlMcpTool(name, input = {}) {
  const appDir = path.join(controllerRepo(), "apps", "control-mcp");
  const child = spawn("pnpm", ["-C", appDir, "start"], {
    env: {
      ...process.env,
      CHIBA3_CONTROL_API_URL: controlApiUrl(),
    },
    stdio: ["pipe", "pipe", "pipe"],
  });

  const pending = new Map();
  const state = { buffer: Buffer.alloc(0) };
  let stderr = "";
  let settled = false;
  let nextId = 1;

  const settleAll = (error) => {
    if (settled) return;
    settled = true;
    for (const { reject } of pending.values()) reject(error);
    pending.clear();
  };

  child.stdout.on("data", (chunk) => {
    try {
      parseMessages(state, chunk, (message) => {
        const entry = pending.get(message.id);
        if (!entry) return;
        pending.delete(message.id);
        if (message.error) {
          entry.reject(new Error(String(message.error.message ?? "mcp_error")));
          return;
        }
        entry.resolve(message.result);
      });
    } catch (error) {
      settleAll(error instanceof Error ? error : new Error(String(error)));
    }
  });

  child.stderr.on("data", (chunk) => {
    stderr += chunk.toString("utf8");
  });

  child.on("error", (error) => {
    settleAll(error);
  });

  child.on("exit", (code, signal) => {
    if (pending.size === 0) return;
    settleAll(
      new Error(
        `mcp_exit:${code ?? "null"}:${signal ?? "null"}${stderr ? `:${stderr.trim()}` : ""}`
      )
    );
  });

  const request = (method, params) =>
    new Promise((resolve, reject) => {
      const id = nextId;
      nextId += 1;
      pending.set(id, { resolve, reject });
      child.stdin.write(encodeMessage({ jsonrpc: "2.0", id, method, params }));
    });

  const notify = (method, params) => {
    child.stdin.write(encodeMessage({ jsonrpc: "2.0", method, params }));
  };

  const timeout = setTimeout(() => {
    settleAll(new Error(`mcp_timeout:${name}`));
    child.kill("SIGTERM");
  }, 30_000);

  try {
    await request("initialize", {
      protocolVersion: "2024-11-05",
      clientInfo: {
        name: "chiba-claw",
        version: "0.1.0",
      },
      capabilities: {},
    });
    notify("notifications/initialized", {});
    const toolResult = await request("tools/call", {
      name,
      arguments: input,
    });
    const text = toolResult?.content?.find?.((row) => row.type === "text")?.text ?? "";
    if (toolResult?.isError) {
      throw new Error(text || `mcp_tool_failed:${name}`);
    }
    return text ? tryParseJson(text) : toolResult;
  } finally {
    clearTimeout(timeout);
    child.kill("SIGTERM");
  }
}

export function mergeResourceIntoSnapshot({ snapshot, kind, resource }) {
  const collectionMap = {
    playlist: "playlists",
    block: "blocks",
    channel: "channels",
    profile: "profiles",
  };
  const collectionKey = collectionMap[kind];
  if (!collectionKey) {
    throw new Error(`unsupported_resource_kind:${kind}`);
  }
  if (!resource || typeof resource !== "object" || typeof resource.id !== "string") {
    throw new Error("resource_id_required");
  }

  const nextSnapshot = structuredClone(snapshot);
  const collection = Array.isArray(nextSnapshot[collectionKey]) ? nextSnapshot[collectionKey] : [];
  const index = collection.findIndex((row) => row.id === resource.id);
  if (index === -1) {
    collection.push(resource);
  } else {
    collection[index] = resource;
  }
  nextSnapshot[collectionKey] = collection;
  return nextSnapshot;
}

export function printJson(data) {
  process.stdout.write(`${JSON.stringify(data, null, 2)}\n`);
}

loadRepoEnvironment();
