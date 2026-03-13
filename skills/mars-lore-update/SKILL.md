---
name: mars-lore-update
description: Sync the Mars lore Google Sheet from an environment-provided public Google Sheets URL or sheet id into a local filesystem corpus, grouped by sheet with one Markdown file per row.
---

# Mars Lore Update

Use this skill when the user wants to refresh the Mars lore corpus from Google Sheets.

## Inputs

- Prefer `MARS_LORE_SHEET_URL` or `MARS_LORE_SHEET_ID` in the environment. In this repo, `LOREBOOK_URL` is also accepted and mapped automatically.
- Optional `MARS_LORE_OUTPUT_DIR` overrides the default output location of `outputs/mars-lore`.

## Workflow

1. Run `node skills/mars-lore-update/scripts/fetch-mars-lore.mjs --json`
2. The script downloads the workbook as `.xlsx`, recreates the target output directory, creates one subdirectory per sheet, and writes one Markdown file per populated row.
3. Use `outputs/mars-lore/index.json` when you need the exact structured row data without opening many Markdown files.
4. After the sync, only inspect the specific sheet or files the user actually cares about.

## Notes

- The first populated row in each sheet is treated as the header row.
- The first column is preferred for filenames; if it is blank, the first populated cell becomes the filename stem.
- Empty cells are preserved in `index.json`, while Markdown bodies only include populated fields.
- For offline testing or fixtures, pass `--from-xlsx /absolute/path/to/file.xlsx`.
