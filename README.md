<div align="center">
  <br />
  <h1>Video Highlight Skill</h1>
  <p><strong>把一个视频交给 Agent，自动分析高光、裁剪片段、生成可阅读网页。</strong></p>
  <p>
    <code>Claude Code</code> · <code>OpenClaw</code> · <code>Codex</code> · <code>Agent Skill</code>
  </p>
  <table>
    <tr>
      <td><strong>Install URL</strong></td>
      <td><code>https://github.com/inhai-wiki/video-highlight-skill.git</code></td>
    </tr>
    <tr>
      <td><strong>Input</strong></td>
      <td>长视频、会议录屏、课程视频、直播回放、产品短视频</td>
    </tr>
    <tr>
      <td><strong>Output</strong></td>
      <td>高光片段、字幕文件、结构化 JSON、观看页式复盘网页</td>
    </tr>
  </table>
  <br />
</div>

## 快速开始

把这个仓库地址发给你的 Agent 框架安装：

```text
https://github.com/inhai-wiki/video-highlight-skill.git
```

然后把视频交给 Agent：

```text
请使用 video-highlight-skill 分析这个视频，自动判断高光片段，完成裁剪，并生成一个可在线阅读的复盘网页。
```

兼容常见 Agent/Skill 安装方式，例如 Claude Code、OpenClaw、Codex，以及支持从 GitHub 安装 Skill 的自研 Agent 框架。

## 它会做什么

- 读取视频元信息
- 抽取音频和关键帧
- 生成时间戳内容索引
- 判断高光片段
- 调用 `ffmpeg` 裁剪视频
- 生成 sidecar SRT 字幕
- 输出一个白底黑字的观看页式网页

生成的网页是左侧主播放器、右侧高光列表的布局。右侧列表会显示高光视频预览，点击后左侧播放器切换到对应片段。页面右上角和底部会展示 GitHub 链接，方便读者下载这个 Skill。

## 案例演示

下面是一条 20 秒产品短视频的分析结果。Skill 将它拆成了 3 个高光段：开头 hook、产品卖点、试喝反馈与 CTA。

<p align="center">
  <img src="examples/poppi-raspberry-rose-contact-sheet.jpg" alt="Poppi Raspberry Rose video highlight demo" width="900" />
</p>

| 高光片段 | 时间 | 作用 |
| --- | --- | --- |
| Skepticism turns into curiosity | 0:00-0:05.2 | 用创作者反应制造开头吸引力 |
| Benefit stack in one beat | 0:05.2-0:12.4 | 集中展示低糖、口味、益生元信息 |
| Taste proof and direct recommendation | 0:12.4-0:20.1 | 通过试喝反馈和 CTA 完成转化 |

案例 JSON：

```text
examples/poppi-raspberry-rose-plan.json
```

生成网页结构：

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

## 适合场景

- 技术分享：提取核心观点、演示片段和复盘页面
- 会议录屏：整理决策、待办、风险和关键讨论
- 课程视频：生成知识点索引和可跳转片段
- 赛事/直播：剪出精彩瞬间和回放集锦
- 产品短视频：拆解 hook、卖点、试用反馈、CTA

## Agent 输出协议

Agent 需要生成一个 `clip_plan.json`。最小结构：

```json
{
  "scenario": "highlight",
  "source_title": "Video title",
  "summary": "Short summary.",
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

## 本地依赖

Agent 运行环境需要：

- Python 3.9+
- `ffmpeg`
- `ffprobe`

语音转写、多模态理解和联网验证由 Agent 框架自行接入。这个 Skill 负责把视频处理、计划校验、裁剪和网页生成稳定封装起来。

## License

MIT
