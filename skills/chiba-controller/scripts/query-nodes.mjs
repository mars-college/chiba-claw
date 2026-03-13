#!/usr/bin/env node

import {
  callControlMcpTool,
  parseArgs,
  printJson,
  readBooleanFlag,
  readOptionalInteger,
  readOptionalString,
  readStringList,
} from "./lib.mjs";

const { flags } = parseArgs(process.argv.slice(2));
const payload = {};

const query = readOptionalString(flags, "query");
const status = readOptionalString(flags, "status");
const namespace = readOptionalString(flags, "namespace");
const registryId = readOptionalString(flags, "registry-id");
const includeRuntime = readBooleanFlag(flags, "include-runtime", false);
const live = flags.inventory ? false : readBooleanFlag(flags, "live", true);
const limit = readOptionalInteger(flags, "limit");
const timeoutMs = readOptionalInteger(flags, "timeout-ms");
const nodeIds = readStringList(flags, "node-id");

if (query) payload.query = query;
if (status) payload.status = status;
if (namespace) payload.namespace = namespace;
if (registryId) payload.registryId = registryId;
if (includeRuntime) payload.includeRuntime = true;
payload.live = live;
if (limit !== undefined) payload.limit = limit;
if (timeoutMs !== undefined) payload.timeoutMs = timeoutMs;
if (nodeIds.length > 0) payload.nodeIds = nodeIds;

const result = await callControlMcpTool("query_nodes", payload);
printJson(result);
