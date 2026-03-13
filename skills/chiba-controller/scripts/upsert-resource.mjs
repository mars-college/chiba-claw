#!/usr/bin/env node

import {
  fetchSnapshot,
  importResources,
  mergeResourceIntoSnapshot,
  parseArgs,
  printJson,
  readJsonInput,
  readRequiredString,
} from "./lib.mjs";

const { flags } = parseArgs(process.argv.slice(2));
const kind = readRequiredString(flags, "kind");
const resource = await readJsonInput(flags);
const snapshot = await fetchSnapshot();
const merged = mergeResourceIntoSnapshot({
  snapshot,
  kind,
  resource,
});

if (flags["dry-run"]) {
  printJson({
    ok: true,
    dryRun: true,
    kind,
    resourceId: resource.id,
    snapshot: merged,
  });
} else {
  const result = await importResources(merged);
  printJson({
    ok: true,
    kind,
    resourceId: resource.id,
    import: result,
  });
}
