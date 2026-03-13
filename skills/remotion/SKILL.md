---
name: remotion
description: Use the local Remotion workspace in skills/remotion to create or edit a video in code and render the final media to outputs/remotion. Use this when the user wants an animation, explainer, ad, or other motion piece built as React and TypeScript.
---

# Remotion

Use this skill when the user wants a video built in code inside this repo.

## Workflow

1. Run `bash skills/remotion/setup.sh`.
2. Inspect `skills/remotion/src/compositions/AgentWorkspace.tsx` and `skills/remotion/src/Root.tsx` to understand the current composition registry.
3. Create or edit a composition under `skills/remotion/src/compositions/`. Prefer a new request-specific file instead of overwriting the starter composition unless the user asked for a revision.
4. Register the composition in `skills/remotion/src/Root.tsx`.
5. Preview or list compositions with:
   - `npm --prefix skills/remotion run dev`
   - `npm --prefix skills/remotion run compositions`
6. Render with `node skills/remotion/scripts/render-remotion.mjs <CompositionId> [--output-name slug.mp4] [-- <extra remotion args>]`.
7. Return the exact file path under `outputs/remotion/`.

## Notes

- The executable Remotion workspace lives entirely under `skills/remotion/`.
- `setup.sh` guarantees a working Node, Python, and FFmpeg toolchain for the skill.
- Use `skills/remotion/scripts/python` and `skills/remotion/scripts/ffmpeg` when you need helper asset generation or post-processing.
- Keep final renders in `outputs/remotion/`.
- Default to MP4 unless the user asked for alpha, GIF, or another format.
