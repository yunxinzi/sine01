# 苏醒 PPT Skill（Suxing PPT Skill）

**8套可视化风格探索 · 完整图稿审核 · 真分层可编辑 · 动画预规划 · 逐页QA · 断点续作**

这是一套基于多轮真实 PPT 制作与失败复盘整理的 **Agent Skills 规范工作流**，面向愿意用 AI 制作高质量演示、同时要求画面忠实度、真实可编辑性、交付可靠性的团队与个人。核心不是“自动把文字塞进模板”，而是“先确定参考图、再按参考图忠实重建、用可证伪的检查确认成果”。

> **重要边界**：本仓库提供可安装的 Skill、参考规范和辅助审计脚本，**不是**开箱即用的 AI 生图/PPT 制作平台。需由宿主 Agent 调用其可用的图片生成器、PPTX 编辑器、渲染器和目标播放软件。没有运行某项验证时，不能宣称通过。

## 功能

- 主题、观众、时长、文字密度等集中澄清；已有决定不再反复询问
- 生成至少8套真实可见、差异明显的视觉样板，由用户选定或混搭
- 用最复杂样页先验证方案，再批量生产全套图稿，用户审核后锁定基准
- 在 editable/hybrid 模式保留原生文本、形状、图表与真正独立前景，拒绝“整页截图假分层”
- 在图稿阶段预留动画对象、运动空间和终态，区分预规划、实装与实播
- 每页按确认画面对照渲染；检测空白、溢出、错字、层级、残影与软件兼容性
- 增量修复、素材缓存、版本化保存和断点续作，不以降低质量来换速度
- 支持完整可编辑版、纯图片版、混合版、PDF-only 与已有PPT审阅模式

## 工作流

`DEFINE → EXPLORE (8 previews) → PILOT → ARTWORK (user approval) → REBUILD → VERIFY → DELIVER`

**人工Gate只有重要缺失、选风格和全稿审核**。用户已经确认的环节自动沿用；明确要求跳过某节点时记录例外。

## Gemini 一键安装

Gemini CLI 直接运行 `gemini skills install https://github.com/yunxinzi/sine01.git --path skills/suxing-ppt-skill`。网页版请使用 Skills 的 ZIP 导入。详细见 [INSTALL_GEMINI.md](INSTALL_GEMINI.md)。

## 安装

下载源码后，把 `suxing-ppt-skill/` 文件夹复制到你的 Agent Skills 目录，例如：

```bash
mkdir -p .agents/skills
cp -r suxing-ppt-skill .agents/skills/
```

请以所用宿主产品的官方文档为准确定 Skills 搜索目录。加载后直接提出“用苏醒 PPT Skill 做一个12页可编辑、16:9的电影推荐PPT，先给我8套风格预览”。

## 本地检查（无需生图 API）

```bash
python3 scripts/validate_skill.py .
python3 scripts/validate_project.py assets/project-template.json
python3 -m unittest discover -s tests -v
# 可选：有实际PPTX后再做对象审计
python3 scripts/audit_pptx.py /path/to/deck.pptx --mode editable
```

> `audit_pptx.py` 是结构**风险扫描**，不能替代 PowerPoint/WPS 真实打开、编辑与动画实播。

## 目录

```text
suxing-ppt-skill/
├── SKILL.md                     # 可直接被Agent加载的主指令
├── references/                 # 图稿、分层、动画、QA、续做与交付细则
├── assets/project-template.json # 唯一事实源示例
├── scripts/                    # 技能校验、工程状态校验、PPTX风险审计、图片差异
├── tests/                      # 标准库单元测试
├── examples/                   # 用户输入与预期阶段产物
├── README.md
├── README_EN.md
├── LICENSE
└── CHANGELOG.md
```

## 设计来源与状态

V1.0–V1.9 反复迭代的经验整合为首个公开候选 `v2.0.0`：把主提示词变成可按需加载的 `SKILL.md` + 独立约束参考文档 + 真实可运行的静态审计工具。此次是**工作流打包和脚本单元测试版**，不是对全自动PPT生成成功率、PPT/WPS兼容性或审美质量的实测保证。

历史修订原则、关键缺陷与修复在 [CHANGELOG](CHANGELOG.md) 中记录。若发现平台兼容问题，欢迎提交Issue附最小复现、PPTX信息、使用软件和截图（去除敏感内容）。

## 协议

MIT License；使用时保留许可声明。第三方模型、模板、图片、字体与文献的授权不由本仓库授予。
