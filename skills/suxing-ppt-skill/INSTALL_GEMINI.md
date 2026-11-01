# Gemini / Antigravity 安装：Suxing PPT Skill

本仓库提供 Agent Skills 工作流，主入口 [SKILL.md](SKILL.md)。它要求宿主有必要的图像生成、PPTX 构建、渲染等工具；**不能把阅读 GitHub 文件当成已安装**。

## Gemini CLI：直接从公开 GitHub 安装

```bash
gemini skills install https://github.com/yunxinzi/sine01.git --path skills/suxing-ppt-skill
```

启动 Gemini CLI 后用 `/skills list` 查找 `suxing-ppt-skill`，必要时执行 `/skills reload`。安装与激活需经过用户权限确认。

## Gemini 网页版与手机 App：导入 ZIP

Gemini Apps 已支持 Skills，但**仅粘贴 GitHub 链接不等于自动注册持久 Skill**。

1. 在 https://gemini.google.com 打开 `Customize → Skills → Create → Upload`。
2. 上传 `Suxing-PPT-Skill-Gemini-Import.zip`，它的根目录就是 `SKILL.md`、`references/` 等。
3. 审核说明并点击创建，确保 Skill 已启用。
4. 在新对话中输入“使用 suxing-ppt-skill 制作 PPT”，或通过 `/` 选择 Skill。

官方目前对 Gemini Apps Skills 的文件、脚本和部分功能有使用限制；不保证在任意对话都能运行 Python、生成可编辑 PPTX 或执行 PowerPoint 实播。应核对实际工具并如实报告。

## Antigravity App/IDE

将本文件夹复制到工作区 `.agents/skills/suxing-ppt-skill/`，或全局 `~/.gemini/config/skills/suxing-ppt-skill/`；按官方文档重载或重新启动，输入 `/suxing-ppt-skill` 或直接提出 PPT 任务。

## 验收清单

- Skill 列表存在 `suxing-ppt-skill`，不是仅能打开 GitHub 页面。
- 激活后可读取 SKILL.md、references 等关联文件。
- 测试“课堂 12 页 PPT”应从需求澄清及 8 套真实风格预览开始，选版之前不能假称完整稿已完成。
- 必须明确区分纯图片版与真实可编辑 PPTX、结构测试与实播测试。

## Google 官方文档

- https://geminicli.com/docs/cli/skills/
- https://support.google.com/gemini/answer/17094296?hl=en
- https://antigravity.google/docs/skills
