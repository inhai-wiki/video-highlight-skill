<div align="center">
  <br />
  <h1>Video Highlight Skill</h1>
  <p>
    Long video analysis, highlight clipping, subtitle sidecars, and a clean online recap page.
  </p>
  <p>
    <strong>Agent Workflow</strong> · <strong>FFmpeg</strong> · <strong>Static Recap Page</strong> · <strong>Codex Skill</strong>
  </p>
  <table>
    <tr>
      <td><strong>Input</strong></td>
      <td>Long videos, meeting recordings, courses, livestreams, product demos</td>
    </tr>
    <tr>
      <td><strong>Output</strong></td>
      <td>Highlight clips, subtitles, structured JSON, white-style share page</td>
    </tr>
    <tr>
      <td><strong>Style</strong></td>
      <td>White background, black text, thin borders, compact cards</td>
    </tr>
  </table>
  <br />
</div>

## 简介

`video-highlight-skill` 是一个面向 Agent 的长视频高光处理 Skill。它把视频分析、时间戳索引、高光筛选、片段裁剪和复盘网页生成串成一条可复用流程。

适合这些场景：

- 技术分享视频：提取高光片段和复盘页面
- 会议录屏：整理决策、待办和关键讨论
- 课程/培训视频：生成时间戳知识点索引
- 直播/赛事回放：定位精彩瞬间并剪成集锦
- 产品短视频：拆解 hook、卖点、试用反馈和 CTA

## 目录结构

```text
video-highlight-skill/
├── SKILL.md
├── README.md
├── agents/
│   └── openai.yaml
├── assets/
│   └── sample_clip_plan.json
├── examples/
│   └── poppi-raspberry-rose-plan.json
├── references/
│   └── analysis-schema.md
└── scripts/
    └── video_highlight.py
```

## 环境依赖

必须安装：

- Python 3.9+
- `ffmpeg`
- `ffprobe`

可选安装：

- Whisper 或其他语音转写工具
- OCR 工具，用于识别视频内字幕
- 任意多模态模型，用于画面理解和高光判断

检查依赖：

```bash
ffmpeg -version
ffprobe -version
python3 --version
```

## 快速开始

创建工作目录：

```bash
python3 scripts/video_highlight.py init-project \
  --output work/demo \
  --scenario highlight
```

探测视频：

```bash
python3 scripts/video_highlight.py probe input.mp4 \
  --output work/demo/metadata.json
```

抽取音频和关键帧：

```bash
python3 scripts/video_highlight.py extract-audio input.mp4 \
  --output work/demo/audio.wav

python3 scripts/video_highlight.py sample-frames input.mp4 \
  --output-dir work/demo/frames \
  --interval 10
```

让 Agent 或模型基于 `references/analysis-schema.md` 生成 `clip_plan.json`，然后校验：

```bash
python3 scripts/video_highlight.py validate-plan work/demo/clip_plan.json
```

裁剪高光片段：

```bash
python3 scripts/video_highlight.py cut input.mp4 \
  --plan work/demo/clip_plan.json \
  --output-dir work/demo/clips
```

生成可托管网页：

```bash
python3 scripts/video_highlight.py page \
  --plan work/demo/clip_plan.json \
  --clips-dir work/demo/clips \
  --source-video input.mp4 \
  --copy-media \
  --output work/demo/site/index.html
```

`work/demo/site/` 可以直接部署到任意静态托管服务。

## 真实案例：20 秒产品短视频拆解

测试视频：一条 20 秒竖屏产品短视频，内容围绕 Poppi Raspberry Rose 饮料展开。Skill 把它拆成 3 个高光段：

| 片段 | 时间 | 内容 | 用途 |
| --- | --- | --- | --- |
| Skepticism turns into curiosity | 0:00-0:05.2 | 创作者对产品营销的第一反应 | 开头 hook |
| Benefit stack in one beat | 0:05.2-0:12.4 | Raspberry rose、5g sugar、prebiotic 信息集中出现 | 产品卖点 |
| Taste proof and direct recommendation | 0:12.4-0:20.1 | 试喝反馈、产品特写、购买建议 | 转化 CTA |

示例计划文件见：

```text
examples/poppi-raspberry-rose-plan.json
```

生成后的网页结构：

```text
site/
├── index.html
└── media/
    ├── source-980.mp4
    └── clips/
        ├── 01-skepticism-turns-into-curiosity.mp4
        ├── 02-benefit-stack-in-one-beat.mp4
        └── 03-taste-proof-and-direct-recommendation.mp4
```

网页采用观看页布局：左侧是主播放器和当前片段拆解，右侧是可滚动的高光列表。点击右侧片段后，左侧播放器会切换到对应高光视频。页面也保留原视频入口，可以跳回原视频的对应时间点。

## JSON 输出协议

模型或 Agent 需要输出严格 JSON。最小结构：

```json
{
  "scenario": "highlight",
  "source_title": "Video title",
  "summary": "Short source video summary.",
  "segments": [],
  "highlights": [
    {
      "start": 0,
      "end": 30,
      "title": "Highlight title",
      "summary": "What happens in this clip.",
      "reason": "Why this clip matters.",
      "score": 90,
      "tags": ["demo"],
      "quote": "Representative quote.",
      "takeaways": ["Key takeaway"],
      "subtitles": []
    }
  ]
}
```

完整协议见 [references/analysis-schema.md](references/analysis-schema.md)。

## 页面能力

`page` 命令会生成一个白底黑字的静态页面：

- 左侧主播放器展示原视频或当前高光片段
- 右侧高光列表独立滚动
- 点击高光列表后，主播放器切换到对应片段
- 每个片段保留独立 MP4
- 支持 source video 时间跳转
- 支持 quote、takeaways、tags、score
- 支持 sidecar SRT 字幕文件
- 使用相对媒体路径，便于部署

## 推荐工作流

1. 先用 `probe` 获取视频长度和编码信息。
2. 长视频按 15-30 秒抽帧；产品短视频按 1-2 秒抽帧。
3. 语音转写和画面观察合并成时间戳索引。
4. 按场景生成 `clip_plan.json`。
5. 用 `validate-plan` 修正时间戳和重叠片段。
6. 用 `cut` 生成 MP4 和 SRT。
7. 用 `page --copy-media` 生成可部署网页。

## 发布建议

把 `site/` 目录部署到 Vercel、Cloudflare Pages、GitHub Pages 或任何静态文件服务即可。

## License

MIT
