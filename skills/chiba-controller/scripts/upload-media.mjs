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
const paths = readStringList(flags, "path");
if (paths.length === 0) {
  throw new Error("path_required");
}

const payload = {
  paths,
  wait: flags["no-wait"] ? false : readBooleanFlag(flags, "wait", true),
};

const artist = readOptionalString(flags, "artist");
const description = readOptionalString(flags, "description");
const playlistTitle = readOptionalString(flags, "playlist-title");
const timeoutMs = readOptionalInteger(flags, "timeout-ms");
const fileTitles = readStringList(flags, "file-title");
const fileArtists = readStringList(flags, "file-artist");
const fileDescriptions = readStringList(flags, "file-description");

if (artist) payload.artist = artist;
if (description) payload.description = description;
if (flags.playlist !== undefined) payload.playlist = readBooleanFlag(flags, "playlist", true);
if (playlistTitle) payload.playlistTitle = playlistTitle;
if (timeoutMs !== undefined) payload.timeoutMs = timeoutMs;
if (fileTitles.length > 0) payload.fileTitles = fileTitles;
if (fileArtists.length > 0) payload.fileArtists = fileArtists;
if (fileDescriptions.length > 0) payload.fileDescriptions = fileDescriptions;

const result = await callControlMcpTool("create_upload_request", payload);
printJson(result);
