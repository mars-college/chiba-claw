#!/usr/bin/env node

import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const skillRoot = path.resolve(scriptDir, "..");
const repoRoot = path.resolve(skillRoot, "../..");
const outputDir = path.join(repoRoot, "outputs", "ytp");

export function slugify(input, fallback = "ytp-clip") {
  const normalized = String(input ?? "")
    .trim()
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "");
  const slug = normalized
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return slug || fallback;
}

function parseCliArguments(argv) {
  const args = {
    ext: "mp4",
    json: false,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === "--json") {
      args.json = true;
      continue;
    }
    if (!token.startsWith("--")) {
      throw new Error(`Unexpected argument: ${token}`);
    }

    const key = token.slice(2);
    const value = argv[index + 1];
    if (value == null || value.startsWith("--")) {
      throw new Error(`Missing value for --${key}`);
    }
    args[key] = value;
    index += 1;
  }

  if (!args.title && !args.filename) {
    throw new Error("Provide --title or --filename.");
  }

  return args;
}

export function resolveOutputPath({ title, filename, ext = "mp4" }) {
  const normalizedExt = String(ext).replace(/^\./, "") || "mp4";
  const resolvedName = filename
    ? path.basename(filename)
    : `${slugify(title)}.${normalizedExt}`;

  return {
    outputDir,
    outputPath: path.join(outputDir, resolvedName),
    filename: resolvedName,
  };
}

function main() {
  const args = parseCliArguments(process.argv.slice(2));
  const payload = resolveOutputPath(args);

  if (args.json) {
    console.log(JSON.stringify(payload, null, 2));
    return;
  }

  console.log(payload.outputPath);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    main();
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  }
}
