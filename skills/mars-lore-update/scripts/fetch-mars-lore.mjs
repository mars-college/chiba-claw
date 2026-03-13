#!/usr/bin/env node

import { readFileSync } from "node:fs";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import ExcelJS from "exceljs";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDir, "../../..");

function defaultOutputDir() {
  const configured = process.env.MARS_LORE_OUTPUT_DIR;
  return configured
    ? path.resolve(configured)
    : path.join(repoRoot, "outputs", "mars-lore");
}

function parseDotEnv(contents) {
  const entries = {};

  for (const rawLine of contents.split(/\r?\n/u)) {
    const line = rawLine.trim();
    if (line === "" || line.startsWith("#")) {
      continue;
    }

    const match = rawLine.match(/^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$/u);
    if (!match) {
      continue;
    }

    const [, key] = match;
    let [, , value] = match;
    value = value.trim();

    if (
      (value.startsWith(`"`) && value.endsWith(`"`)) ||
      (value.startsWith(`'`) && value.endsWith(`'`))
    ) {
      const quote = value[0];
      value = value.slice(1, -1);
      if (quote === `"`) {
        value = value
          .replace(/\\n/g, "\n")
          .replace(/\\r/g, "\r")
          .replace(/\\"/g, `"`)
          .replace(/\\\\/g, "\\");
      }
    } else {
      value = value.replace(/\s+#.*$/u, "").trim();
    }

    entries[key] = value;
  }

  return entries;
}

function setIfMissing(key, value) {
  if (value == null || value === "" || normalizeValue(process.env[key]) !== "") {
    return;
  }

  process.env[key] = value;
}

export function loadRepoEnvironment(
  envFile = process.env.CHIBA_CLAW_ENV_FILE || path.join(repoRoot, ".env")
) {
  try {
    const contents = readFileSync(envFile, "utf8");
    const entries = parseDotEnv(contents);

    for (const [key, value] of Object.entries(entries)) {
      setIfMissing(key, value);
    }
  } catch (error) {
    if (error && typeof error === "object" && "code" in error && error.code === "ENOENT") {
      return false;
    }
    throw error;
  }

  if (
    normalizeValue(process.env.MARS_LORE_SHEET_URL) === "" &&
    normalizeValue(process.env.MARS_LORE_SHEET_ID) === "" &&
    normalizeValue(process.env.LOREBOOK_URL) !== ""
  ) {
    process.env.MARS_LORE_SHEET_URL = normalizeValue(process.env.LOREBOOK_URL);
  }

  return true;
}

function normalizeValue(value) {
  return String(value ?? "").trim();
}

function stringifyCellValue(value) {
  if (value == null) {
    return "";
  }

  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return normalizeValue(value);
  }

  if (value instanceof Date) {
    return value.toISOString();
  }

  if (Array.isArray(value)) {
    return normalizeValue(value.join(" "));
  }

  if (typeof value === "object") {
    if ("richText" in value && Array.isArray(value.richText)) {
      return normalizeValue(value.richText.map((item) => item.text ?? "").join(""));
    }

    if ("text" in value && normalizeValue(value.text) !== "") {
      return normalizeValue(value.text);
    }

    if ("result" in value && value.result != null) {
      return stringifyCellValue(value.result);
    }

    if ("formula" in value && normalizeValue(value.formula) !== "") {
      return normalizeValue(value.formula);
    }

    if ("hyperlink" in value && normalizeValue(value.hyperlink) !== "") {
      return normalizeValue(value.hyperlink);
    }

    if ("error" in value && normalizeValue(value.error) !== "") {
      return normalizeValue(value.error);
    }
  }

  return normalizeValue(value);
}

function rowHasContent(row) {
  return row.some((cell) => normalizeValue(cell) !== "");
}

function slugify(input, fallback = "untitled") {
  const normalized = normalizeValue(input)
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "");
  const slug = normalized
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return slug || fallback;
}

function uniqueSlug(baseSlug, usedSlugs) {
  const count = usedSlugs.get(baseSlug) ?? 0;
  usedSlugs.set(baseSlug, count + 1);
  return count === 0 ? baseSlug : `${baseSlug}-${count + 1}`;
}

function normalizeHeaders(headerRow, width) {
  const seen = new Map();
  const headers = [];

  for (let index = 0; index < width; index += 1) {
    const rawHeader = normalizeValue(headerRow[index]) || `Column ${index + 1}`;
    const count = seen.get(rawHeader) ?? 0;
    seen.set(rawHeader, count + 1);
    headers.push(count === 0 ? rawHeader : `${rawHeader} (${count + 1})`);
  }

  return headers;
}

function findHeaderRow(rows) {
  const headerIndex = rows.findIndex(rowHasContent);
  if (headerIndex === -1) {
    throw new Error("Workbook sheet has no populated rows.");
  }
  return headerIndex;
}

function createMarkdownDocument({ title, sheetName, rowNumber, fields }) {
  const populatedFields = Object.entries(fields).filter(([, value]) => {
    return normalizeValue(value) !== "";
  });

  const lines = [
    `# ${title}`,
    "",
    `- Source sheet: ${sheetName}`,
    `- Source row: ${rowNumber}`,
    "",
    "## Fields",
    ""
  ];

  if (populatedFields.length === 0) {
    lines.push("_No populated fields in this row._", "");
  } else {
    for (const [header, value] of populatedFields) {
      lines.push(`### ${header}`, "", String(value), "");
    }
  }

  return `${lines.join("\n").trimEnd()}\n`;
}

function parseCliArguments(argv) {
  const args = {
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

export function parseGoogleSheetId(input) {
  const value = normalizeValue(input);
  if (value === "") {
    throw new Error("Google Sheet reference is empty.");
  }

  const directIdMatch = value.match(/^[A-Za-z0-9-_]{20,}$/);
  if (directIdMatch) {
    return value;
  }

  const urlMatch = value.match(/\/spreadsheets\/d\/([A-Za-z0-9-_]+)/);
  if (urlMatch) {
    return urlMatch[1];
  }

  throw new Error(`Could not parse Google Sheet id from: ${value}`);
}

export function resolveSheetReference() {
  return (
    normalizeValue(process.env.MARS_LORE_SHEET_URL) ||
    normalizeValue(process.env.MARS_LORE_SHEET_ID) ||
    normalizeValue(process.env.LOREBOOK_URL)
  );
}

async function loadWorkbookBuffer({ workbookPath, sheetReference }) {
  if (workbookPath) {
    return fs.readFile(path.resolve(workbookPath));
  }

  const sheetId = parseGoogleSheetId(sheetReference);
  const exportUrl = `https://docs.google.com/spreadsheets/d/${sheetId}/export?format=xlsx`;
  const response = await fetch(exportUrl);

  if (!response.ok) {
    throw new Error(`Failed to download workbook: ${response.status} ${response.statusText}`);
  }

  return Buffer.from(await response.arrayBuffer());
}

async function loadWorkbook(buffer) {
  const workbook = new ExcelJS.Workbook();
  await workbook.xlsx.load(buffer);
  return workbook;
}

function worksheetToRows(worksheet) {
  const width = worksheet.columnCount;
  const rows = [];

  for (let rowNumber = 1; rowNumber <= worksheet.rowCount; rowNumber += 1) {
    const row = worksheet.getRow(rowNumber);
    rows.push(
      Array.from({ length: width }, (_, columnOffset) => {
        return stringifyCellValue(row.getCell(columnOffset + 1).value);
      })
    );
  }

  return rows;
}

export async function syncMarsLore({
  workbookPath,
  sheetReference = resolveSheetReference(),
  outDir = defaultOutputDir()
} = {}) {
  if (!workbookPath && !sheetReference) {
    throw new Error(
      "Provide --from-xlsx or set MARS_LORE_SHEET_URL / MARS_LORE_SHEET_ID. LOREBOOK_URL is also accepted."
    );
  }

  const workbookBuffer = await loadWorkbookBuffer({ workbookPath, sheetReference });
  const workbook = await loadWorkbook(workbookBuffer);

  await fs.rm(outDir, {
    recursive: true,
    force: true
  });
  await fs.mkdir(outDir, {
    recursive: true
  });

  const generatedAt = new Date().toISOString();
  const manifest = {
    generatedAt,
    outputDir: path.resolve(outDir),
    source: workbookPath
      ? {
          type: "file",
          path: path.resolve(workbookPath)
        }
      : {
          type: "google-sheet",
          id: parseGoogleSheetId(sheetReference)
        },
    sheetCount: 0,
    entryCount: 0,
    sheets: []
  };

  const usedSheetDirectories = new Map();

  for (const worksheet of workbook.worksheets) {
    const sheetName = worksheet.name;
    const rows = worksheetToRows(worksheet);

    if (!rows.some(rowHasContent)) {
      continue;
    }

    const headerIndex = findHeaderRow(rows);
    const dataRows = rows.slice(headerIndex + 1);
    const width = Math.max(
      rows[headerIndex].length,
      ...dataRows.map((row) => row.length),
      0
    );
    const headers = normalizeHeaders(rows[headerIndex], width);
    const sheetDirectory = uniqueSlug(slugify(sheetName, "sheet"), usedSheetDirectories);
    const sheetOutputDir = path.join(outDir, sheetDirectory);
    const usedEntrySlugs = new Map();

    await fs.mkdir(sheetOutputDir, {
      recursive: true
    });

    const entries = [];

    for (let rowOffset = 0; rowOffset < dataRows.length; rowOffset += 1) {
      const row = dataRows[rowOffset];
      if (!rowHasContent(row)) {
        continue;
      }

      const rowNumber = headerIndex + rowOffset + 2;
      const values = Array.from({ length: width }, (_, index) => normalizeValue(row[index]));
      const fields = Object.fromEntries(headers.map((header, index) => [header, values[index] ?? ""]));
      const preferredTitle = values[0] || values.find((value) => value !== "") || `row-${rowNumber}`;
      const entrySlug = uniqueSlug(slugify(preferredTitle, `row-${rowNumber}`), usedEntrySlugs);
      const entryFileName = `${entrySlug}.md`;
      const entryPath = path.join(sheetOutputDir, entryFileName);
      const relativePath = path.posix.join(sheetDirectory, entryFileName);

      await fs.writeFile(
        entryPath,
        createMarkdownDocument({
          title: preferredTitle,
          sheetName,
          rowNumber,
          fields
        }),
        "utf8"
      );

      entries.push({
        title: preferredTitle,
        slug: entrySlug,
        path: relativePath,
        rowNumber,
        fields
      });
    }

    manifest.sheets.push({
      name: sheetName,
      directory: sheetDirectory,
      headers,
      entryCount: entries.length,
      entries
    });
    manifest.entryCount += entries.length;
  }

  manifest.sheetCount = manifest.sheets.length;

  await fs.writeFile(
    path.join(outDir, "index.json"),
    `${JSON.stringify(manifest, null, 2)}\n`,
    "utf8"
  );

  return manifest;
}

function formatSummary(manifest) {
  return {
    sheetCount: manifest.sheetCount,
    entryCount: manifest.entryCount,
    outputDir: manifest.outputDir
  };
}

async function main() {
  try {
    const args = parseCliArguments(process.argv.slice(2));
    const manifest = await syncMarsLore({
      workbookPath: args["from-xlsx"],
      sheetReference: args["sheet-url"] ?? args["sheet-id"],
      outDir: args.out ? path.resolve(args.out) : defaultOutputDir()
    });

    if (args.json) {
      console.log(JSON.stringify(formatSummary(manifest), null, 2));
      return;
    }

    console.log(
      `Synced ${manifest.entryCount} entries across ${manifest.sheetCount} sheets to ${manifest.outputDir}`
    );
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  }
}

const executedAsScript =
  process.argv[1] != null && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);

loadRepoEnvironment();

if (executedAsScript) {
  await main();
}
