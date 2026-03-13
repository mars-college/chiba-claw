#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const skillRoot = path.resolve(scriptDir, "..");
const repoRoot = path.resolve(skillRoot, "../..");
const outputDir = path.join(repoRoot, "outputs", "remotion");
const entryPoint = path.join(skillRoot, "src", "index.ts");
const remotionBin = path.join(skillRoot, "node_modules", ".bin", "remotion");

function parseCliArguments(argv) {
  const args = {
    json: false,
    dryRun: false,
    extraArgs: [],
  };

  const passthroughIndex = argv.indexOf("--");
  const effectiveArgv = passthroughIndex === -1 ? argv : argv.slice(0, passthroughIndex);
  args.extraArgs = passthroughIndex === -1 ? [] : argv.slice(passthroughIndex + 1);

  for (let index = 0; index < effectiveArgv.length; index += 1) {
    const token = effectiveArgv[index];
    if (token === "--json") {
      args.json = true;
      continue;
    }
    if (token === "--dry-run") {
      args.dryRun = true;
      continue;
    }
    if (token === "--output-name") {
      const value = effectiveArgv[index + 1];
      if (value == null || value.startsWith("--")) {
        throw new Error("Missing value for --output-name");
      }
      args.outputName = value;
      index += 1;
      continue;
    }
    if (token.startsWith("--")) {
      throw new Error(`Unexpected argument: ${token}`);
    }
    if (!args.compositionId) {
      args.compositionId = token;
      continue;
    }
    throw new Error(`Unexpected positional argument: ${token}`);
  }

  if (!args.compositionId) {
    throw new Error("Provide a composition id to render.");
  }

  return args;
}

function normalizeOutputName(compositionId, outputName) {
  const fallback = `${compositionId}.mp4`;
  const fileName = path.basename(outputName || fallback);

  if (/\.(mp4|mov|gif|webm)$/i.test(fileName)) {
    return fileName;
  }

  return `${fileName}.mp4`;
}

export function buildRenderPlan({ compositionId, outputName, extraArgs = [] }) {
  const normalizedOutputName = normalizeOutputName(compositionId, outputName);
  const outputPath = path.join(outputDir, normalizedOutputName);
  return {
    compositionId,
    outputDir,
    outputPath,
    cwd: skillRoot,
    command: [remotionBin, "render", "src/index.ts", compositionId, outputPath, ...extraArgs],
  };
}

function main() {
  const args = parseCliArguments(process.argv.slice(2));
  const plan = buildRenderPlan(args);

  if (args.json) {
    console.log(JSON.stringify(plan, null, 2));
    if (args.dryRun) {
      return;
    }
  }

  if (args.dryRun) {
    if (!args.json) {
      console.log(plan.outputPath);
    }
    return;
  }

  if (!fs.existsSync(remotionBin)) {
    throw new Error("Run bash skills/remotion/setup.sh before rendering.");
  }

  fs.mkdirSync(outputDir, {
    recursive: true,
  });

  const result = spawnSync(plan.command[0], plan.command.slice(1), {
    cwd: plan.cwd,
    stdio: "inherit",
  });

  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }

  if (!args.json) {
    console.log(plan.outputPath);
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    main();
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  }
}
