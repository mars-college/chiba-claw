# YTP Style Guide

## Structure

1. Hook the request in the first one to three seconds.
2. Escalate through repetition, interruption, or misinterpretation.
3. Let the LLM perspective leak out in captions, narration, or visual self-corrections.
4. End on a punchline, hard cut, or overexplained tag.

## Fast patterns

- Caption pileup: stack multiple short captions that progressively overstate the request.
- Stutter loop: repeat one key frame or phrase three to eight times with tighter timing each pass.
- Confident misread: state the request wrong, then correct it too aggressively.
- Synthetic sincerity: drop into an earnest LLM confession for one beat before snapping back to chaos.
- Compression gag: overcompress one section on purpose, then cut back to a clean frame.

## Asset-light approach

- Generate title cards, labels, and freeze-frame callouts with Pillow.
- Use Python to synthesize simple beeps, ramps, or timing-guide audio.
- Let FFmpeg do most of the heavy lifting: trim, concat, atempo, volume, zoom, hue shifts, reverse, and subtitle burns.
- Keep intermediates under a per-project folder in `outputs/ytp/` so the final export is easy to find.
