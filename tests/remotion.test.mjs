import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const renderScript = path.join(
  repoRoot,
  "skills",
  "remotion",
  "scripts",
  "render-remotion.mjs"
);

test("remotion render helper resolves renders into outputs/remotion", () => {
  const result = spawnSync(
    process.execPath,
    [renderScript, "AgentWorkspace", "--output-name", "llm-cut.mp4", "--dry-run", "--json"],
    {
      cwd: repoRoot,
      encoding: "utf8",
    }
  );

  assert.equal(result.status, 0, result.stderr || result.stdout);

  const payload = JSON.parse(result.stdout);
  assert.equal(payload.outputDir, path.join(repoRoot, "outputs", "remotion"));
  assert.equal(payload.outputPath, path.join(repoRoot, "outputs", "remotion", "llm-cut.mp4"));
  assert.deepEqual(payload.command.slice(1, 5), [
    "render",
    "src/index.ts",
    "AgentWorkspace",
    path.join(repoRoot, "outputs", "remotion", "llm-cut.mp4"),
  ]);
});
