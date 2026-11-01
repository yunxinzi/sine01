# 附带脚本与边界

脚本均使用 Python 3.10+，除图像对比脚本外只依赖标准库。

- `scripts/validate_skill.py`: 检查 Agent Skills 元信息、内部相对链接和基础目录结构；不代表平台官方认证。
- `scripts/validate_project.py`: 检查 project.json schema、阶段门槛声明和素材映射，属于**声明一致性检查**，不等于用户真的确认过。
- `scripts/audit_pptx.py`: 解析 PPTX ZIP/XML，统计页面对象、文本框、图片和动画结构；可标记整页一图与空白。无法证明图片真透明、字体匹配、背景无残影、在 WPS 可编辑或动画可播放。
- `scripts/compare_renders.py`: 比较两张等尺寸渲染图，输出绝对误差热力图与MAE。需要 `Pillow`（可 `pip install Pillow`）；视觉数值只辅助人审。

示例：

```bash
python scripts/validate_skill.py .
python scripts/validate_project.py assets/project-template.json
python scripts/audit_pptx.py path/to/deck.pptx --mode editable --json build/audit.json
python scripts/compare_renders.py reference/slide-01.png builds/run-01/preview/slide-01.png --heatmap build/heatmap-01.png
```

未包含任何生成模型 API key，未绑定特定商业供应商，外部工具的版权、权限、价格和限额由使用者自行管理。
