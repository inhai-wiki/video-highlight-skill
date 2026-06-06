---
name: video-highlight-skill
description: Long-video agent workflow for analyzing videos, building timestamped content indexes, selecting highlights, creating clip plans, cutting clips with subtitles, and generating recap pages. Use when Codex is asked to turn long videos, meeting recordings, course videos, livestreams, sports or esports replays, product demos, talks, or conference recordings into highlight reels, structured reports, meeting notes, timestamped course indexes, or shareable recap packages.
---

# Video Highlight Skill

Use this skill to convert a long video into a structured content product: highlight clips, a recap page, a meeting summary, a course index, or a report.

## Workflow

1. Create a work directory.
   - Run `scripts/video_highlight.py init-project --output <workdir> --scenario <highlight|meeting|course|live|report>`.
   - Keep all generated files in that work directory.

2. Inspect the source video.
   - Run `scripts/video_highlight.py probe <video> --output <workdir>/metadata.json`.
   - Use duration, dimensions, and stream metadata to choose frame sampling and clip limits.

3. Extract analysis inputs.
   - Run `scripts/video_highlight.py extract-audio <video> --output <workdir>/audio.wav` for transcription.
   - Run `scripts/video_highlight.py sample-frames <video> --output-dir <workdir>/frames --interval 30` for visual review.
   - Lower `--interval` to 5-15 seconds for sports, demos, UI walkthroughs, or visually dense videos.

4. Build a timestamped index.
   - Transcribe audio with the available speech or multimodal model.
   - Review sampled frames and key visual changes.
   - Merge transcript and visual observations into the JSON shape described in `references/analysis-schema.md`.

5. Select outputs by scenario.
   - `highlight`: choose moments with strong technical value, clear conclusions, demos, audience reaction, or shareable explanation.
   - `meeting`: choose decisions, blockers, owners, action items, risks, and unresolved questions.
   - `course`: segment by knowledge point and produce navigable timestamps.
   - `live`: identify event spikes, major actions, crowd reactions, key commentary, score changes, and turning points.
   - `report`: produce an executive summary, claims to verify, key data, and evidence timestamps.

6. Validate the model plan.
   - Save the model output to `<workdir>/clip_plan.json`.
   - Run `scripts/video_highlight.py validate-plan <workdir>/clip_plan.json`.
   - Fix invalid times, overlapping clips, missing titles, or clips shorter than 3 seconds.

7. Cut clips and generate subtitles.
   - Run `scripts/video_highlight.py cut <video> --plan <workdir>/clip_plan.json --output-dir <workdir>/clips`.
   - The script writes MP4 clips plus sidecar SRT files when subtitle entries are present.

8. Generate a recap page.
   - Run `scripts/video_highlight.py page --plan <workdir>/clip_plan.json --clips-dir <workdir>/clips --source-video <video> --copy-media --output <workdir>/site/index.html`.
   - The page opens with the original video, then lists each highlight with its clip, timestamp, reason, tags, and jump button back to the matching moment in the original video.
   - Return `<workdir>/site/index.html`, generated clips, and any limitations.

## Model Output Contract

Always ask the model for strict JSON. Read `references/analysis-schema.md` before prompting the model, validating output, or adding a new scenario.

Required top-level fields:

- `scenario`
- `source_title`
- `summary`
- `segments`
- `highlights`

Each highlight must include `start`, `end`, `title`, `summary`, `reason`, and `score`.

Use seconds for `start` and `end` when possible. `HH:MM:SS` strings are accepted by the script.

## Practical Defaults

- Target 3-8 highlights for a 1-2 hour video.
- Keep clips between 20 and 120 seconds unless the user asks for a different format.
- Leave 1-3 seconds of context before and after a clip when it improves readability.
- Prefer exact timestamps from transcript alignment over inferred frame timestamps.
- For technical talks, give demos, architecture explanations, surprising results, and final takeaways higher scores.
- For meetings, avoid promotional language. Preserve decisions, owners, deadlines, and open questions.

## Script Reference

Run:

```bash
python3 video-highlight-skill/scripts/video_highlight.py --help
```

Main commands:

- `init-project`: create folders plus prompt and JSON skeleton files.
- `probe`: write ffprobe metadata.
- `extract-audio`: create a 16 kHz mono WAV for transcription.
- `sample-frames`: create periodic JPG frames for visual analysis.
- `validate-plan`: validate the model JSON plan.
- `cut`: cut clips and write subtitle sidecars.
- `page`: generate a white, Vercel-style static recap page.

## Recap Page Output

Use `--source-video` and `--copy-media` when the user wants a page that can be hosted online.

Recommended command:

```bash
python3 video-highlight-skill/scripts/video_highlight.py page \
  --plan <workdir>/clip_plan.json \
  --clips-dir <workdir>/clips \
  --source-video <video> \
  --copy-media \
  --output <workdir>/site/index.html
```

This creates:

- `<workdir>/site/index.html`
- `<workdir>/site/media/source-<video-name>`
- `<workdir>/site/media/clips/*.mp4`

The generated page uses a minimal black-and-white visual system: white background, black text, thin borders, compact cards, and no decorative gradients. The first screen shows the original video. Highlight cards appear below with generated clip playback and a button that jumps the original video to the same timestamp.

## Quality Checks

Before final delivery:

- Confirm all clip files exist and have non-zero size.
- Confirm clip titles are specific enough to stand alone.
- Confirm timestamps match visible or spoken content.
- Confirm the recap page opens locally and video paths are relative under `site/`.
- Mention when subtitles are sidecar SRT files rather than burned into video.
