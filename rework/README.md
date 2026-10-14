# 8 秒 MG 视觉返工工程

本次只制作 `Rework8Sec`，240 帧、8 秒、1920×1080、30 FPS、H.264/AAC。取原歌曲 27.866667–35.866667s：「很贪心，要全世界注意」。旧版全片保留，不把此次样片视为已完成全片视觉返工。

## 查看

- `output/rework/8s-sample.mp4`：最终方向验证样片（V3）。
- `rework/review/v3-seconds.jpg`：真实 MP4 的精确逐秒关键帧，另含最后一帧。
- `rework/review/v3-transitions.jpg`：23 个真实运动/转场帧。
- `rework/art-direction.md`：参考与失败成片的诊断，主导创意与取舍。
- `rework/storyboard-8s.md`：在实现前写出的镜头、字头和重音分镜。
- `rework/iteration-log.md`：三版实渲的拒绝理由与修订。
- `output/rework/media-qa.json`：完整解码、音频相关性、字体和几何验证。

## 修改与渲染

Node 22/24、npm、FFmpeg、Chromium。全部依赖固定在 package-lock.json。本地音乐与字体已随工程保留。

```bash
npm ci
npm run dev
npm run rework:render
npm run rework:qa
npm run rework:verify
```

Studio 选择 `Rework8Sec`。新镜头在 `src/rework/Rework8Sec.tsx`，粗字挤出、角色、心形与运动工具在 `src/rework/visual-language.tsx`。不使用旧版的 Stage/Window/Caption 模板（只复用字体加载）。每个镜头有独立语义、构图和动作函数，动画完全按帧计算。

运行渲染命令得到 `output/rework/sample-v3.mp4`；交付版 `8s-sample.mp4` 为其相同字节的副本。默认 Chromium 路径 `/usr/bin/chromium` 可在 `scripts/render-rework.mjs` 修改。审查 Python 脚本依赖 requirements-helpers.txt；正常 Studio 和渲染无需 Python。

原歌词绝对时间保留在 lyrics-timing.json。当前样片使用单字锚点：很 0.4、贪 50.7、心 64.9、要 114.7、全 129.4、世 144.4、界 154.9、注 168.4、意 195.7 帧。落点峰值参考实测音乐瞬态；例如「要」在第 115 帧启动，第 120 帧完成拍击。源码中的这些值可直接手工修正。

指定的六个设计 Skill 在当前云环境未找到，未伪称使用。实际使用可访问的 Remotion 技能与参考片分析指导制作；如果之后提供这些 Skill 的路径，应只吸收与参考一致的要求。

## 审查边界

所有 240 帧解码通过，无黑帧。精确逐秒和过渡帧已做视觉审查，三版返工记录已保留。原音频相关系数约 0.9992，偏移约 25ms。源 YRC 与音频瞬态支持字头和重音设计，但没有人工逐字听审或 ASR 强制对齐。艺术质量最终仍需按参考与实际播放判断，不能由技术检查数代替。
