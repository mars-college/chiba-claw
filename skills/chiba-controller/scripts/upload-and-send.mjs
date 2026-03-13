#!/usr/bin/env node

import {
  applyTarget,
  callControlMcpTool,
  DEFAULT_CONTROLLER_ID,
  DEFAULT_NAMESPACE,
  DEFAULT_REGISTRY_ID,
  parseArgs,
  printJson,
  readBooleanFlag,
  readOptionalInteger,
  readOptionalString,
  readStringList,
} from "./lib.mjs";

const { flags } = parseArgs(process.argv.slice(2));
const paths = readStringList(flags, "path");
const nodeIds = readStringList(flags, "screen-id");

if (paths.length === 0) throw new Error("path_required");
if (nodeIds.length === 0) throw new Error("screen_id_required");

const uploadPayload = {
  paths,
  wait: flags["no-wait"] ? false : readBooleanFlag(flags, "wait", true),
};

for (const [flag, key] of [
  ["artist", "artist"],
  ["description", "description"],
  ["playlist-title", "playlistTitle"],
]) {
  const value = readOptionalString(flags, flag);
  if (value) uploadPayload[key] = value;
}

if (flags.playlist !== undefined) {
  uploadPayload.playlist = readBooleanFlag(flags, "playlist", true);
}

const timeoutMs = readOptionalInteger(flags, "timeout-ms");
if (timeoutMs !== undefined) uploadPayload.timeoutMs = timeoutMs;

for (const [flag, key] of [
  ["file-title", "fileTitles"],
  ["file-artist", "fileArtists"],
  ["file-description", "fileDescriptions"],
]) {
  const values = readStringList(flags, flag);
  if (values.length > 0) uploadPayload[key] = values;
}

const uploadResult = await callControlMcpTool("create_upload_request", uploadPayload);
const job = uploadResult?.job ?? null;
const result = job?.result ?? uploadResult?.result ?? null;
const mediaId =
  result?.media?.id ??
  (Array.isArray(result?.imported?.media) ? result.imported.media[0]?.id : undefined);
const playlistId =
  result?.playlistId ??
  (Array.isArray(result?.imported?.playlists) ? result.imported.playlists[0]?.id : undefined);
const targetKind =
  readBooleanFlag(flags, "send-playlist", false) || (!mediaId && typeof playlistId === "string")
    ? "playlist"
    : "media";
const targetId = targetKind === "playlist" ? playlistId : mediaId;

if (typeof targetId !== "string" || targetId.trim() === "") {
  throw new Error("upload_completed_without_sendable_target");
}

const launch = {};
const mode = readOptionalString(flags, "mode");
const displayRotate = readOptionalInteger(flags, "display-rotate");
if (mode) launch.mode = mode;
if (displayRotate !== undefined) launch.displayRotate = displayRotate;
if (readBooleanFlag(flags, "lock", false)) launch.lock = true;
if (readBooleanFlag(flags, "qr", false)) launch.qr = true;
if (readBooleanFlag(flags, "nosplash", false)) launch.nosplash = true;

const applyResult = await applyTarget({
  targetKind,
  targetId,
  nodeIds,
  namespace: readOptionalString(flags, "namespace") || DEFAULT_NAMESPACE,
  registryId: readOptionalString(flags, "registry-id") || DEFAULT_REGISTRY_ID,
  controllerId: readOptionalString(flags, "controller-id") || DEFAULT_CONTROLLER_ID,
  dryRun: readBooleanFlag(flags, "dry-run-send", false),
  launch,
});

printJson({
  ok: true,
  upload: uploadResult,
  send: applyResult,
  chosenTarget: {
    kind: targetKind,
    id: targetId,
  },
});
