#!/usr/bin/env node

import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDir, "../../..");

function defaultRootDir() {
  const configured = process.env.MARS_LORE_OUTPUT_DIR;
  return configured
    ? path.resolve(configured)
    : path.join(repoRoot, "outputs", "mars-lore");
}

function parseCliArguments(argv) {
  const args = {
    limit: "5",
    json: false
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

  return args;
}

function tokenize(input) {
  const matches = String(input ?? "").toLowerCase().match(/[\p{L}\p{N}]+/gu) ?? [];
  return [...new Set(matches.filter((term) => term.length > 1))];
}

async function walkMarkdownFiles(rootDir) {
  const entries = await fs.readdir(rootDir, {
    withFileTypes: true
  });
  const files = [];

  for (const entry of entries) {
    const entryPath = path.join(rootDir, entry.name);
    if (entry.isDirectory()) {
      files.push(...(await walkMarkdownFiles(entryPath)));
      continue;
    }

    if (entry.isFile() && entry.name.endsWith(".md")) {
      files.push(entryPath);
    }
  }

  return files.sort();
}

function countOccurrences(haystack, needle) {
  let count = 0;
  let searchIndex = 0;

  while (true) {
    const matchIndex = haystack.indexOf(needle, searchIndex);
    if (matchIndex === -1) {
      return count;
    }
    count += 1;
    searchIndex = matchIndex + needle.length;
  }
}

function extractTitle(content, fallbackPath) {
  const titleMatch = content.match(/^#\s+(.+)$/m);
  return titleMatch?.[1]?.trim() || path.basename(fallbackPath, ".md");
}

function buildPreview(content, terms) {
  const flattened = content.replace(/\s+/g, " ").trim();
  const lowered = flattened.toLowerCase();
  let firstHit = -1;

  for (const term of terms) {
    const hitIndex = lowered.indexOf(term);
    if (hitIndex !== -1 && (firstHit === -1 || hitIndex < firstHit)) {
      firstHit = hitIndex;
    }
  }

  if (firstHit === -1) {
    return flattened.slice(0, 180);
  }

  const start = Math.max(0, firstHit - 70);
  const end = Math.min(flattened.length, firstHit + 110);
  let preview = flattened.slice(start, end);

  if (start > 0) {
    preview = `...${preview}`;
  }
  if (end < flattened.length) {
    preview = `${preview}...`;
  }

  return preview;
}

export async function searchLoreDirectory({
  rootDir = defaultRootDir(),
  query,
  limit = 5
} = {}) {
  if (!query || String(query).trim() === "") {
    throw new Error("Provide a non-empty search query.");
  }

  const resolvedRoot = path.resolve(rootDir);
  const terms = tokenize(query);
  if (terms.length === 0) {
    throw new Error("Search query must contain at least one word or number.");
  }

  const markdownFiles = await walkMarkdownFiles(resolvedRoot);
  const results = [];
  const queryLower = String(query).toLowerCase();

  for (const filePath of markdownFiles) {
    const content = await fs.readFile(filePath, "utf8");
    const title = extractTitle(content, filePath);
    const relativePath = path.relative(resolvedRoot, filePath).split(path.sep).join("/");
    const titleLower = title.toLowerCase();
    const contentLower = content.toLowerCase();
    const pathLower = relativePath.toLowerCase();
    const combined = `${pathLower}\n${titleLower}\n${contentLower}`;

    let score = 0;
    const matchedTerms = [];

    for (const term of terms) {
      const pathHits = countOccurrences(pathLower, term);
      const titleHits = countOccurrences(titleLower, term);
      const contentHits = countOccurrences(contentLower, term);
      const totalHits = pathHits + titleHits + contentHits;

      if (totalHits > 0) {
        matchedTerms.push(term);
        score += pathHits * 6;
        score += titleHits * 10;
        score += contentHits * 2;
      }
    }

    if (combined.includes(queryLower)) {
      score += terms.length * 8;
    }
    if (matchedTerms.length === terms.length) {
      score += terms.length * 5;
    }

    if (score > 0) {
      results.push({
        title,
        path: relativePath,
        score,
        matchedTerms,
        preview: buildPreview(content, terms)
      });
    }
  }

  return results
    .sort((left, right) => right.score - left.score || left.path.localeCompare(right.path))
    .slice(0, Number(limit));
}

async function main() {
  try {
    const args = parseCliArguments(process.argv.slice(2));
    const rootDir = args.root ? path.resolve(args.root) : defaultRootDir();
    const limit = Number(args.limit);

    if (!Number.isFinite(limit) || limit < 1) {
      throw new Error("--limit must be a positive integer.");
    }

    const results = await searchLoreDirectory({
      rootDir,
      query: args.query,
      limit
    });

    if (args.json) {
      console.log(
        JSON.stringify(
          {
            rootDir,
            query: args.query,
            results
          },
          null,
          2
        )
      );
      return;
    }

    if (results.length === 0) {
      console.log(`No matches found in ${rootDir}`);
      return;
    }

    for (const [index, result] of results.entries()) {
      console.log(`${index + 1}. ${result.title}`);
      console.log(`   ${result.path}`);
      console.log(`   score=${result.score} matched=${result.matchedTerms.join(", ")}`);
      console.log(`   ${result.preview}`);
    }
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  }
}

const executedAsScript =
  process.argv[1] != null && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);

if (executedAsScript) {
  await main();
}

