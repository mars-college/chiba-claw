#!/usr/bin/env node

import {
  applyTarget,
  DEFAULT_CONTROLLER_ID,
  DEFAULT_NAMESPACE,
  DEFAULT_REGISTRY_ID,
  parseArgs,
  printJson,
  readBooleanFlag,
  readOptionalInteger,
  readOptionalString,
  readRequiredString,
  readStringList,
} from "./lib.mjs";

const { flags } = parseArgs(process.argv.slice(2));
const targetKind = readRequiredString(flags, "target-kind");
const targetId = readRequiredString(flags, "target-id");
const nodeIds = readStringList(flags, "screen-id");

if (nodeIds.length === 0) {
  throw new Error("screen_id_required");
}

const launch = {};
const mode = readOptionalString(flags, "mode");
const theme = readOptionalString(flags, "theme");
const displayRotate = readOptionalInteger(flags, "display-rotate");
const hudMode = readOptionalString(flags, "hud-mode");
const hudSec = readOptionalInteger(flags, "hud-sec");

if (mode) launch.mode = mode;
if (theme) launch.theme = theme;
if (displayRotate !== undefined) launch.displayRotate = displayRotate;
if (readBooleanFlag(flags, "lock", false)) launch.lock = true;
if (readBooleanFlag(flags, "qr", false)) launch.qr = true;
if (readBooleanFlag(flags, "nosplash", false)) launch.nosplash = true;
if (hudMode) launch.hudMode = hudMode;
if (hudSec !== undefined) launch.hudShowSec = hudSec;

const result = await applyTarget({
  targetKind,
  targetId,
  nodeIds,
  namespace: readOptionalString(flags, "namespace") || DEFAULT_NAMESPACE,
  registryId: readOptionalString(flags, "registry-id") || DEFAULT_REGISTRY_ID,
  controllerId: readOptionalString(flags, "controller-id") || DEFAULT_CONTROLLER_ID,
  dryRun: readBooleanFlag(flags, "dry-run", false),
  launch,
});

printJson(result);
