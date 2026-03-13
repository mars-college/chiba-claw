---
name: ytp
description: Create short YouTube Poop style videos about the user's request using Python and FFmpeg, then render the result to outputs/ytp. Use this when the user wants a fast-cut, self-aware remix with a personal LLM point of view.
---

# YTP

Use this skill when the user wants a short, chaotic, clearly request-driven remix video.

## Workflow

1. Run `bash skills/ytp/setup.sh`.
2. Turn the user's request into the subject of the bit, not just background inspiration.
3. Build the piece with Python plus FFmpeg.
   - Use `skills/ytp/scripts/python` for generation and orchestration.
   - Use `skills/ytp/scripts/ffmpeg` for the final encode and any glitch, cut, speed, or subtitle passes.
   - Use `node skills/ytp/scripts/create-output-path.mjs --title "<request>"` to get a safe final output path under `outputs/ytp/`.
4. Keep the result short, usually 8 to 30 seconds, and make the user's request unmistakable in the opening seconds.
5. Return the exact final file path under `outputs/ytp/`.

## Creative constraints

- The video should be about the user's request. Echo their phrasing, goal, object of attention, or constraints in captions, narration, source selection, or punchlines.
- Give it a personal LLM spin: recursive self-correction, token anxiety, label spam, synthetic sincerity, or overexplained confidence all fit.
- Prefer speed and density over polish. Hard cuts, repeats, freeze-frames, pitch shifts, zoom punches, and awkward sincerity are all valid.
- Use local or generated assets first. Pull external media only when it materially improves the joke or clarity.
- If you want more pattern ideas, load `references/style-guide.md`.
