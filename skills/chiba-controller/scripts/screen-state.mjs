#!/usr/bin/env node

import {
  callControlMcpTool,
  parseArgs,
  printJson,
  readOptionalString,
  readRequiredString,
} from "./lib.mjs";

const { flags } = parseArgs(process.argv.slice(2));
const screenId = readRequiredString(flags, "screen-id");
const namespace = readOptionalString(flags, "namespace");

const payload = { screenId };
if (namespace) payload.namespace = namespace;

const result = await callControlMcpTool("node_state", payload);
printJson(result);
