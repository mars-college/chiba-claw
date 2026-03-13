#!/usr/bin/env node

import { callControlMcpTool, parseArgs, printJson, readJsonInput, readRequiredString } from "./lib.mjs";

const { flags } = parseArgs(process.argv.slice(2));
const tool = readRequiredString(flags, "tool");
const input = await readJsonInput(flags).catch(() => ({}));
const result = await callControlMcpTool(tool, input);
printJson(result);
