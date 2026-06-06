# Analysis Schema

Use this reference when preparing prompts, validating model output, or extending the skill to a new video scenario.

## Strict JSON Shape

```json
{
  "scenario": "highlight",
  "source_title": "Talk or video title",
  "summary": "One paragraph summary of the whole source video.",
  "segments": [
    {
      "start": 0,
      "end": 120,
      "title": "Opening and context",
      "summary": "What happens in this time range.",
      "visuals": ["speaker on stage", "architecture diagram"],
      "topics": ["agent workflow", "video analysis"],
      "importance": 3
    }
  ],
  "highlights": [
    {
      "start": 305.2,
      "end": 365.8,
      "title": "Agent completes the first end-to-end cut",
      "summary": "The speaker shows the long-video workflow completing analysis, clipping, subtitles, and recap page generation.",
      "reason": "Clear end-to-end proof point with visible output.",
      "score": 92,
      "tags": ["demo", "workflow"],
      "quote": "The agent has now generated the first highlight clip.",
      "takeaways": ["The workflow can run end to end.", "The result is ready for a recap page."],
      "subtitles": [
        {
          "start": 305.2,
          "end": 309.7,
          "text": "The agent has now generated the first highlight clip."
        }
      ]
    }
  ],
  "report": {
    "key_points": ["Main conclusion"],
    "claims_to_verify": [
      {
        "claim": "Specific factual claim made in the video.",
        "timestamp": 425.0,
        "verification_status": "not_checked"
      }
    ],
    "action_items": [
      {
        "task": "Follow-up task",
        "owner": "Unknown",
        "due": ""
      }
    ]
  }
}
```

## Prompt Pattern

Ask the model to produce only JSON:

```text
Analyze this long video using the transcript, frame observations, and metadata below.
Return strict JSON matching the schema. Do not include markdown.

Scenario: <highlight|meeting|course|live|report>
Target clips: <number>
Clip duration: <min>-<max> seconds

Selection rules:
- Prefer moments with clear standalone value.
- Use exact timestamps from transcript alignment.
- Include subtitle entries when transcript timing is available.
- Include `quote` and `takeaways` when a recap page needs richer highlight breakdowns.
- Avoid overlapping highlights unless the user asked for a montage.

Metadata:
<metadata>

Transcript:
<timestamped transcript>

Visual observations:
<frame observations>
```

## Scenario Scoring

`highlight` scoring:

- 90-100: strong standalone demo, major reveal, memorable conclusion, or audience reaction
- 75-89: useful explanation, concrete example, crisp technical point
- 60-74: context that supports a stronger nearby clip
- below 60: keep in segments, skip as highlight

`meeting` scoring:

- Decisions and owner-bound action items score highest.
- Risks, blockers, deadlines, and unresolved questions are useful.
- Casual discussion without a decision should stay in segments.

`course` scoring:

- Each segment should represent one teachable unit.
- Prefer clean boundaries around topic changes.
- Use `highlights` for must-watch moments or examples.

`live` scoring:

- Score visual action, commentary intensity, crowd reaction, score changes, and replay-worthy turning points.
- Sample frames more frequently than speech-heavy videos.

`report` scoring:

- Prioritize claims, evidence, data points, conclusions, and contradictions.
- Add factual claims to `report.claims_to_verify`.

## Validation Rules

- `end` must be greater than `start`.
- Clip duration should be at least 3 seconds.
- `score` should be 0-100.
- Timestamps must be within the source video duration when metadata is available.
- Titles should be concise and specific.
- Summaries should explain what the viewer will see or learn.
