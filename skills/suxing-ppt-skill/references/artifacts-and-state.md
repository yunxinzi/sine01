# 文件与状态约定

## 推荐项目目录（示例）

```
workspace/<project_id>/
  project.json                  # 唯一事实源（可使用 assets/project-template.json）
  styleboards/01.png ... 08.png
  reference/slide-01.png ...
  assets/backgrounds/*.png
  assets/foregrounds/*.png
  builds/<build_id>/deck.pptx
  builds/<build_id>/deck.pdf
  builds/<build_id>/preview/slide-01.png ...
  builds/<build_id>/qa-report.json
```

素材引用用相对路径；同一构建版本绑定同一 `build_id`。保存每个产物的 SHA-256，禁止拿旧 PDF/图片冒充最新 PPTX 的导出。可选 `manifest` 字段记录 `build_id`, `source_build_id`, `renderer`, `export_timestamp`, `actual_verification`。

## 各模式交付
- `editable`: 真实可编辑 `.pptx`、全页预览；按需 `.pdf`、可重建素材和动画描述。
- `image`: 纯图片 `.pptx` 与逐页图片（按需 PDF），必须明确“不能分层编辑”，禁止夸大。
- `hybrid`: `.pptx` 与按页的编辑性边界表，明确 `flattened` 素材。
- `pdf-only`: PDF 与按需预览，不声称 PPTX 已有。
- `review`: QA报告、已修改文件和差异说明；修改后仍执行受影响页面验证。

## 跨环境运行
工程所需生成/渲染/校验工具因Agent而异。优先使用实际可运行的工具组合；不把某一种Python/PPT生成库写死为工作流必要条件。若某项条件无法满足，精确说明影响范围并给出能诚实交付的产物。
