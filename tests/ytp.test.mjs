import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const outputPathScript = path.join(
  repoRoot,
  "skills",
  "ytp",
  "scripts",
  "create-output-path.mjs"
);

test("ytp output helper resolves outputs into outputs/ytp", () => {
  const result = spawnSync(
    process.execPath,
    [outputPathScript, "--title", "What is it like to be a LLM?", "--json"],
    {
      cwd: repoRoot,
      encoding: "utf8",
    }
  );

  assert.equal(result.status, 0, result.stderr || result.stdout);

  const payload = JSON.parse(result.stdout);
  assert.equal(payload.outputDir, path.join(repoRoot, "outputs", "ytp"));
  assert.equal(payload.filename, "what-is-it-like-to-be-a-llm.mp4");
  assert.equal(
    payload.outputPath,
    path.join(repoRoot, "outputs", "ytp", "what-is-it-like-to-be-a-llm.mp4")
  );
});
