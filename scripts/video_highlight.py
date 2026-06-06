#!/usr/bin/env python3
import argparse
import html
import json
import shutil
import subprocess
from pathlib import Path


SCENARIOS = {"highlight", "meeting", "course", "live", "report"}


def run_command(args):
    try:
        subprocess.run(args, check=True)
    except FileNotFoundError as exc:
        raise SystemExit(f"Missing executable: {args[0]}") from exc
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"Command failed with exit code {exc.returncode}: {' '.join(args)}") from exc


def parse_time(value):
    if isinstance(value, (int, float)):
        return float(value)
    if value is None:
        raise ValueError("missing timestamp")
    text = str(value).strip()
    if not text:
        raise ValueError("empty timestamp")
    if ":" not in text:
        return float(text)
    parts = [float(part) for part in text.split(":")]
    if len(parts) == 3:
        hours, minutes, seconds = parts
    elif len(parts) == 2:
        hours = 0
        minutes, seconds = parts
    else:
        raise ValueError(f"invalid timestamp: {value}")
    return hours * 3600 + minutes * 60 + seconds


def format_timestamp(seconds):
    seconds = max(0.0, float(seconds))
    whole = int(seconds)
    millis = int(round((seconds - whole) * 1000))
    if millis == 1000:
        whole += 1
        millis = 0
    hours = whole // 3600
    minutes = (whole % 3600) // 60
    secs = whole % 60
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def safe_slug(text, fallback):
    allowed = []
    for char in str(text).lower():
        if char.isalnum():
            allowed.append(char)
        elif char in {" ", "-", "_"}:
            allowed.append("-")
    slug = "".join(allowed).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or fallback


def load_plan(path):
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, list):
        data = {"scenario": "highlight", "source_title": "", "summary": "", "segments": [], "highlights": data}
    return data


def get_highlights(plan):
    items = plan.get("highlights") or plan.get("clips") or []
    if not isinstance(items, list):
        raise ValueError("highlights must be a list")
    return items


def relative_url(path, base_dir):
    try:
        return Path(path).resolve().relative_to(Path(base_dir).resolve()).as_posix()
    except ValueError:
        return Path(path).as_posix()


def copy_media_file(src, media_dir, prefix=""):
    source = Path(src)
    if not source.exists():
        return source
    media_dir.mkdir(parents=True, exist_ok=True)
    target_name = f"{prefix}{source.name}" if prefix else source.name
    target = media_dir / target_name
    if source.resolve() != target.resolve():
        shutil.copy2(source, target)
    return target


def render_tags(tags):
    if not tags:
        return ""
    items = "\n".join(f"<span>{html.escape(str(tag))}</span>" for tag in tags)
    return f'<div class="tags">{items}</div>'


def render_takeaways(takeaways):
    if not takeaways:
        return ""
    items = "\n".join(f"<li>{html.escape(str(item))}</li>" for item in takeaways)
    return f'<ul class="takeaways">{items}</ul>'


def render_report(plan):
    report = plan.get("report") or {}
    key_points = report.get("key_points") or []
    claims = report.get("claims_to_verify") or []
    actions = report.get("action_items") or []
    blocks = []
    if key_points:
        items = "\n".join(f"<li>{html.escape(str(item))}</li>" for item in key_points)
        blocks.append(f"<section class=\"notes\"><h2>Key Points</h2><ul>{items}</ul></section>")
    if claims:
        items = []
        for claim in claims:
            timestamp = claim.get("timestamp", "")
            status = claim.get("verification_status", "")
            items.append(
                "<li>"
                f"{html.escape(str(claim.get('claim', '')))}"
                f"<span>{html.escape(str(timestamp))} · {html.escape(str(status))}</span>"
                "</li>"
            )
        blocks.append(f"<section class=\"notes\"><h2>Claims</h2><ul>{''.join(items)}</ul></section>")
    if actions:
        items = []
        for action in actions:
            owner = action.get("owner", "")
            due = action.get("due", "")
            items.append(
                "<li>"
                f"{html.escape(str(action.get('task', '')))}"
                f"<span>{html.escape(str(owner))} {html.escape(str(due))}</span>"
                "</li>"
            )
        blocks.append(f"<section class=\"notes\"><h2>Action Items</h2><ul>{''.join(items)}</ul></section>")
    if not blocks:
        return ""
    return f"<div class=\"notes-grid\">{''.join(blocks)}</div>"


def validate_plan_data(plan, duration=None):
    errors = []
    scenario = plan.get("scenario")
    if scenario and scenario not in SCENARIOS:
        errors.append(f"scenario must be one of {sorted(SCENARIOS)}")
    highlights = get_highlights(plan)
    if not highlights:
        errors.append("highlights is empty")
    last_end = -1.0
    for index, item in enumerate(highlights, start=1):
        prefix = f"highlight {index}"
        try:
            start = parse_time(item.get("start"))
            end = parse_time(item.get("end"))
        except Exception as exc:
            errors.append(f"{prefix}: invalid start/end: {exc}")
            continue
        if end <= start:
            errors.append(f"{prefix}: end must be greater than start")
        if end - start < 3:
            errors.append(f"{prefix}: duration is shorter than 3 seconds")
        if duration is not None and end > duration:
            errors.append(f"{prefix}: end exceeds video duration")
        if start < last_end:
            errors.append(f"{prefix}: overlaps previous highlight")
        last_end = max(last_end, end)
        if not str(item.get("title", "")).strip():
            errors.append(f"{prefix}: missing title")
        if not str(item.get("summary", "")).strip():
            errors.append(f"{prefix}: missing summary")
        score = item.get("score", 0)
        try:
            score = float(score)
            if score < 0 or score > 100:
                errors.append(f"{prefix}: score must be 0-100")
        except Exception:
            errors.append(f"{prefix}: score must be numeric")
    return errors


def cmd_init_project(args):
    out = Path(args.output)
    for name in ["frames", "clips", "notes"]:
        (out / name).mkdir(parents=True, exist_ok=True)
    scenario = args.scenario
    skeleton = {
        "scenario": scenario,
        "source_title": "",
        "summary": "",
        "segments": [],
        "highlights": [],
        "report": {"key_points": [], "claims_to_verify": [], "action_items": []},
    }
    (out / "clip_plan.json").write_text(json.dumps(skeleton, ensure_ascii=False, indent=2), encoding="utf-8")
    prompt = (
        "Analyze the video inputs and return strict JSON matching video-highlight-skill/references/analysis-schema.md.\n"
        f"Scenario: {scenario}\n"
        "Use exact timestamps. Include highlights with start, end, title, summary, reason, score, tags, and subtitles when available.\n"
    )
    (out / "model_prompt.txt").write_text(prompt, encoding="utf-8")
    print(f"Created project at {out}")


def cmd_probe(args):
    command = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        args.video,
    ]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise SystemExit("Missing executable: ffprobe") from exc
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.stderr or "ffprobe failed") from exc
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(result.stdout, encoding="utf-8")
    print(f"Wrote metadata to {args.output}")


def cmd_extract_audio(args):
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    run_command([
        "ffmpeg",
        "-y",
        "-i",
        args.video,
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        args.output,
    ])
    print(f"Wrote audio to {args.output}")


def cmd_sample_frames(args):
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    vf = f"fps=1/{args.interval},scale='min({args.width},iw)':-2"
    if args.max_frames:
        vf = f"{vf},trim=end_frame={args.max_frames}"
    run_command([
        "ffmpeg",
        "-y",
        "-i",
        args.video,
        "-vf",
        vf,
        "-q:v",
        "3",
        str(out / "frame_%05d.jpg"),
    ])
    print(f"Wrote frames to {out}")


def write_srt(path, subtitles, clip_start):
    lines = []
    for index, sub in enumerate(subtitles, start=1):
        start = parse_time(sub.get("start")) - clip_start
        end = parse_time(sub.get("end")) - clip_start
        text = str(sub.get("text", "")).strip()
        if not text or end <= 0:
            continue
        lines.extend([
            str(index),
            f"{format_timestamp(max(0, start))} --> {format_timestamp(max(0, end))}",
            text,
            "",
        ])
    if lines:
        path.write_text("\n".join(lines), encoding="utf-8")


def cmd_validate_plan(args):
    plan = load_plan(args.plan)
    duration = parse_time(args.duration) if args.duration else None
    errors = validate_plan_data(plan, duration=duration)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print("Plan is valid")


def cmd_cut(args):
    plan = load_plan(args.plan)
    errors = validate_plan_data(plan)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    generated = []
    for index, item in enumerate(get_highlights(plan), start=1):
        start = parse_time(item["start"])
        end = parse_time(item["end"])
        title = item.get("title", f"clip-{index}")
        slug = safe_slug(title, f"clip-{index:02}")
        clip_path = out / f"{index:02d}-{slug}.mp4"
        command = ["ffmpeg", "-y", "-ss", str(start), "-to", str(end), "-i", args.video]
        if args.copy:
            command.extend(["-map", "0", "-c", "copy"])
        else:
            command.extend(["-map", "0:v:0", "-map", "0:a?", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac"])
        command.append(str(clip_path))
        run_command(command)
        subtitles = item.get("subtitles") or []
        if subtitles:
            write_srt(clip_path.with_suffix(".srt"), subtitles, start)
        generated.append(str(clip_path))
    manifest = {"source": args.video, "clips": generated}
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(generated)} clips to {out}")


def cmd_page(args):
    plan = load_plan(args.plan)
    clips_dir = Path(args.clips_dir)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    media_dir = out.parent / args.media_dir
    title = plan.get("source_title") or "Video Recap"
    summary = plan.get("summary") or ""
    source_video_markup = ""
    if args.source_video:
        source_path = Path(args.source_video)
        if args.copy_media:
            source_path = copy_media_file(source_path, media_dir, prefix="source-")
        source_rel = html.escape(relative_url(source_path, out.parent))
        source_video_markup = f"""
        <section class="source-shell">
          <div class="source-video">
            <video id="sourceVideo" controls preload="metadata" src="{source_rel}"></video>
          </div>
          <aside class="source-notes">
            <span class="eyebrow">Original Video</span>
            <h2>{html.escape(str(title))}</h2>
            <p>{html.escape(str(summary))}</p>
            <div class="source-stats">
              <div><strong>{len(get_highlights(plan))}</strong><span>highlights</span></div>
              <div><strong>{html.escape(str(plan.get('scenario', 'highlight')))}</strong><span>scenario</span></div>
            </div>
          </aside>
        </section>
        """
    else:
        source_video_markup = f"""
        <section class="source-shell no-source">
          <aside class="source-notes wide">
            <span class="eyebrow">Video Recap</span>
            <h2>{html.escape(str(title))}</h2>
            <p>{html.escape(str(summary))}</p>
          </aside>
        </section>
        """
    cards = []
    for index, item in enumerate(get_highlights(plan), start=1):
        start = parse_time(item.get("start"))
        end = parse_time(item.get("end"))
        slug = safe_slug(item.get("title", ""), f"clip-{index:02}")
        expected = clips_dir / f"{index:02d}-{slug}.mp4"
        if not expected.exists():
            matches = sorted(clips_dir.glob(f"{index:02d}-*.mp4"))
            expected = matches[0] if matches else expected
        if args.copy_media and expected.exists():
            expected = copy_media_file(expected, media_dir / "clips")
            srt = Path(expected).with_suffix(".srt")
            original_srt = (clips_dir / expected.name).with_suffix(".srt")
            if original_srt.exists() and not srt.exists():
                copy_media_file(original_srt, media_dir / "clips")
        rel = html.escape(relative_url(expected, out.parent))
        tags = render_tags(item.get("tags") or [])
        takeaways = render_takeaways(item.get("takeaways") or [])
        quote = item.get("quote")
        quote_markup = f"<blockquote>{html.escape(str(quote))}</blockquote>" if quote else ""
        subtitle_count = len(item.get("subtitles") or [])
        subtitle_note = f"<span>{subtitle_count} subtitle lines</span>" if subtitle_count else ""
        card = f"""
        <article class="clip-card">
          <div class="clip-index">{index:02d}</div>
          <div class="clip-media">
            <video controls preload="metadata" src="{rel}"></video>
          </div>
          <div class="clip-body">
            <div class="meta">
              <span>{html.escape(format_seconds(start))} - {html.escape(format_seconds(end))}</span>
              <span>Score {html.escape(str(item.get('score', '')))}</span>
              {subtitle_note}
            </div>
            <h2>{html.escape(str(item.get('title', f'Clip {index}')))}</h2>
            <p>{html.escape(str(item.get('summary', '')))}</p>
            {quote_markup}
            <p class="reason">{html.escape(str(item.get('reason', '')))}</p>
            {takeaways}
            {tags}
            <button class="jump-button" type="button" data-start="{html.escape(str(start))}">Play this moment in original</button>
          </div>
        </article>
        """
        cards.append(card)
    report = render_report(plan)
    doc = PAGE_TEMPLATE.format(
        title=html.escape(str(title)),
        summary=html.escape(str(summary)),
        source_video=source_video_markup,
        cards="\n".join(cards),
        report=report,
    )
    out.write_text(doc, encoding="utf-8")
    print(f"Wrote page to {out}")


def format_seconds(seconds):
    seconds = int(round(float(seconds)))
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours:
        return f"{hours:02}:{minutes:02}:{secs:02}"
    return f"{minutes:02}:{secs:02}"


PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #fafafa;
      --text: #0a0a0a;
      --muted: #666666;
      --soft: #8a8a8a;
      --line: #e5e5e5;
      --accent: #000000;
      --panel: #ffffff;
      --subtle: #f5f5f5;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
    }}
    a {{ color: inherit; }}
    header {{
      padding: 28px min(6vw, 72px) 20px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }}
    .nav {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      font-size: 13px;
      color: var(--muted);
    }}
    .brand {{
      color: var(--text);
      font-weight: 650;
    }}
    h1 {{ margin: 24px 0 10px; max-width: 920px; font-size: clamp(34px, 5vw, 72px); line-height: 0.98; letter-spacing: 0; }}
    .summary {{ max-width: 860px; color: var(--muted); line-height: 1.65; font-size: 17px; }}
    main {{ max-width: 1240px; margin: 0 auto; padding: 24px 20px 56px; }}
    .source-shell {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) 360px;
      gap: 18px;
      align-items: stretch;
      margin: 6px 0 36px;
    }}
    .source-shell.no-source {{
      grid-template-columns: 1fr;
    }}
    .source-video,
    .source-notes,
    .clip-card,
    .notes {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
    }}
    .source-video {{ padding: 10px; }}
    .source-video video {{ display: block; }}
    .source-notes {{
      padding: 22px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      min-height: 260px;
    }}
    .source-notes.wide {{ min-height: 180px; }}
    .eyebrow {{
      display: inline-flex;
      width: max-content;
      padding: 4px 8px;
      border: 1px solid var(--line);
      border-radius: 999px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 650;
      text-transform: uppercase;
      letter-spacing: 0;
    }}
    .source-notes h2 {{ margin: 18px 0 8px; font-size: 24px; line-height: 1.15; letter-spacing: 0; }}
    .source-notes p {{ margin: 0; }}
    .source-stats {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      margin-top: 22px;
    }}
    .source-stats div {{
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--subtle);
    }}
    .source-stats strong {{ display: block; font-size: 22px; }}
    .source-stats span {{ color: var(--soft); font-size: 12px; }}
    .section-heading {{
      display: flex;
      justify-content: space-between;
      align-items: end;
      gap: 14px;
      margin-bottom: 14px;
    }}
    .section-heading h2 {{ margin: 0; font-size: 28px; letter-spacing: 0; }}
    .section-heading p {{ margin: 0; max-width: 520px; color: var(--muted); font-size: 14px; }}
    .clip-card {{
      display: grid;
      grid-template-columns: 52px minmax(280px, 42%) 1fr;
      gap: 18px;
      margin-bottom: 18px;
      padding: 12px;
    }}
    .clip-index {{
      width: 40px;
      height: 40px;
      display: grid;
      place-items: center;
      border: 1px solid var(--line);
      border-radius: 8px;
      color: var(--muted);
      font-size: 13px;
      font-weight: 700;
      background: var(--subtle);
    }}
    video {{ width: 100%; aspect-ratio: 16 / 9; background: #050505; border-radius: 6px; }}
    .clip-body {{ padding: 4px 4px 4px 0; }}
    .meta {{ display: flex; flex-wrap: wrap; gap: 8px; color: var(--muted); font-size: 12px; font-weight: 650; }}
    .meta span {{ padding: 3px 7px; border: 1px solid var(--line); border-radius: 999px; background: var(--subtle); }}
    h2 {{ margin: 8px 0; font-size: 22px; letter-spacing: 0; }}
    p {{ line-height: 1.6; color: var(--muted); }}
    .reason {{ color: var(--text); }}
    blockquote {{
      margin: 14px 0;
      padding: 12px 14px;
      border-left: 3px solid var(--text);
      background: var(--subtle);
      color: var(--text);
      line-height: 1.55;
    }}
    .takeaways {{
      margin: 12px 0 0;
      padding-left: 18px;
      color: var(--muted);
      line-height: 1.55;
    }}
    .tags {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 14px 0; }}
    .tags span {{
      padding: 4px 8px;
      border: 1px solid var(--line);
      border-radius: 999px;
      color: var(--muted);
      font-size: 12px;
      background: var(--panel);
    }}
    .jump-button {{
      appearance: none;
      border: 1px solid var(--text);
      border-radius: 6px;
      background: var(--text);
      color: #ffffff;
      padding: 9px 12px;
      font: inherit;
      font-size: 13px;
      font-weight: 650;
      cursor: pointer;
    }}
    .jump-button:hover {{ background: #333333; }}
    .notes-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 18px;
      margin-top: 28px;
    }}
    .notes {{ padding: 18px; }}
    .notes h2 {{ margin: 0 0 12px; font-size: 18px; }}
    .notes ul {{ margin: 0; padding-left: 18px; color: var(--muted); line-height: 1.6; }}
    .notes li + li {{ margin-top: 10px; }}
    .notes li span {{ display: block; color: var(--soft); font-size: 12px; margin-top: 2px; }}
    @media (max-width: 760px) {{
      header {{ padding-left: 20px; padding-right: 20px; }}
      .source-shell {{ grid-template-columns: 1fr; }}
      .clip-card {{ grid-template-columns: 1fr; }}
      .clip-index {{ width: 100%; height: 34px; }}
      .clip-body {{ padding: 0; }}
      .section-heading {{ display: block; }}
      .notes-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="nav">
      <div class="brand">Video Recap</div>
      <div>Generated highlight analysis</div>
    </div>
    <h1>{title}</h1>
    <div class="summary">{summary}</div>
  </header>
  <main>
    {source_video}
    <section class="section-heading">
      <h2>Highlights</h2>
      <p>Each segment includes the generated clip, source timestamp, selection reason, and analysis notes.</p>
    </section>
    {cards}
    {report}
  </main>
  <script>
    const sourceVideo = document.getElementById('sourceVideo');
    document.querySelectorAll('[data-start]').forEach((button) => {{
      button.addEventListener('click', () => {{
        if (!sourceVideo) return;
        sourceVideo.currentTime = Number(button.dataset.start || 0);
        sourceVideo.play();
        sourceVideo.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
      }});
    }});
  </script>
</body>
</html>
"""


def build_parser():
    parser = argparse.ArgumentParser(description="Long-video highlight workflow helper.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init-project", help="Create a work directory and starter files.")
    p.add_argument("--output", required=True)
    p.add_argument("--scenario", choices=sorted(SCENARIOS), default="highlight")
    p.set_defaults(func=cmd_init_project)

    p = sub.add_parser("probe", help="Write ffprobe metadata JSON.")
    p.add_argument("video")
    p.add_argument("--output", required=True)
    p.set_defaults(func=cmd_probe)

    p = sub.add_parser("extract-audio", help="Extract mono 16 kHz WAV audio.")
    p.add_argument("video")
    p.add_argument("--output", required=True)
    p.set_defaults(func=cmd_extract_audio)

    p = sub.add_parser("sample-frames", help="Sample periodic frames for visual analysis.")
    p.add_argument("video")
    p.add_argument("--output-dir", required=True)
    p.add_argument("--interval", type=float, default=30)
    p.add_argument("--width", type=int, default=1280)
    p.add_argument("--max-frames", type=int, default=0)
    p.set_defaults(func=cmd_sample_frames)

    p = sub.add_parser("validate-plan", help="Validate clip plan JSON.")
    p.add_argument("plan")
    p.add_argument("--duration", default="")
    p.set_defaults(func=cmd_validate_plan)

    p = sub.add_parser("cut", help="Cut clips from a source video using a clip plan.")
    p.add_argument("video")
    p.add_argument("--plan", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--copy", action="store_true", help="Use stream copy instead of re-encoding.")
    p.set_defaults(func=cmd_cut)

    p = sub.add_parser("page", help="Generate an HTML recap page.")
    p.add_argument("--plan", required=True)
    p.add_argument("--clips-dir", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--source-video", default="", help="Original source video shown at the top of the page.")
    p.add_argument("--copy-media", action="store_true", help="Copy source video and clips into a publishable media folder.")
    p.add_argument("--media-dir", default="media", help="Media directory relative to the output page.")
    p.set_defaults(func=cmd_page)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
