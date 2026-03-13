#!/usr/bin/env node

import {
  DEFAULT_NAMESPACE,
  listScreenAssignments,
  parseArgs,
  printJson,
  readOptionalString,
} from "./lib.mjs";

const { flags } = parseArgs(process.argv.slice(2));
const namespace = readOptionalString(flags, "namespace") || DEFAULT_NAMESPACE;
const screenId = readOptionalString(flags, "screen-id");

const result = await listScreenAssignments({ namespace, screenId });
printJson(result);
