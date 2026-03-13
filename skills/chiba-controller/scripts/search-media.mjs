#!/usr/bin/env node

import {
  callControlMcpTool,
  parseArgs,
  printJson,
  readBooleanFlag,
  readOptionalInteger,
  readOptionalString,
} from "./lib.mjs";

const { flags } = parseArgs(process.argv.slice(2));

const payload = {};
const query = readOptionalString(flags, "query");
const sourceType = readOptionalString(flags, "source-type");
const limit = readOptionalInteger(flags, "limit");
const cache =
  flags.cache == null && flags["no-cache"] == null
    ? undefined
    : readBooleanFlag(flags, "cache", flags["no-cache"] ? false : undefined);

if (query) payload.query = query;
if (sourceType) payload.sourceType = sourceType;
if (typeof cache === "boolean") payload.cache = cache;
if (limit !== undefined) payload.limit = limit;

const result = await callControlMcpTool("search_media_library", payload);
printJson(result);
