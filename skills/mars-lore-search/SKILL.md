---
name: mars-lore-search
description: Search the structured Mars lore filesystem corpus under outputs/mars-lore and return only the most relevant files, snippets, and paths so the agent can progressively disclose details without loading the whole directory.
---

# Mars Lore Search

Use this skill when the user wants to find Mars people, lore, captions, or other entries inside the generated Mars lore corpus.

## Workflow

1. Run `node skills/mars-lore-search/scripts/search-mars-lore.mjs --query "<terms>" --json`
2. Read the ranked results and open only the top one to three files, or the exact files the user asks for.
3. If results are noisy, tighten the query with a sheet name, handle, or distinctive phrase instead of broadening the context.

## Notes

- The default corpus location is `outputs/mars-lore`, or `MARS_LORE_OUTPUT_DIR` if it is set.
- The search script returns snippets and scores, not full file bodies.
- Do not dump entire directories of Markdown into context. Use the search output to decide which files to inspect next.

