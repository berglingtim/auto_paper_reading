# 更新日志

版本规则：主版本.次版本.修订号；大更新（新功能/结构变化）本地 git 提交并记录版本号。

---

## v0.1.0（2026-08-09）项目初始化：核心管线跑通

**本次改动**
- 建立项目结构：`src/auto_paper_reading` 核心包、`tools/build_docx.js` 排版脚本、`tests/`、`papers/`、`output/`
- 解析层（`parser/`）：`.pdf` 用 pymupdf 解析；`.doc/.docx` 经 WPS `word2pdf` 转 PDF 后统一走 PDF 管线；统一数据模型 `PaperDocument`/`FigureRef`
- 配图裁剪（`figures.py`）：光栅图直接读取裁剪 + 矢量图按图注（Figure N/图 N）定位裁剪；图注关联、页码/尺寸记录
- 讲解生成（`explain.py` + `llm.py`）：DeepSeek/Kimi/OpenAI 兼容的 LLM 客户端；四部分结构化讲解 prompt（方法灵感与期刊/方法/变换过程/创新点）
- docx 排版（`tools/build_docx.js`，基于 docx skill 的 docx-js）：中文微软雅黑、图文混排、图片按版心自适应缩放
- CLI（`run.py` → `cli.py`）：`prep`（解析裁剪）/`content`（视觉筛选+LLM 生成）/`docx`（排版+WPS 转 PDF 渲染校验）三阶段
- 工作流（`SKILL.md`）：Agent 讲解论文的完整流程（kimi-ai-hybrid vision 选图 → 撰写 content.json → 生成 docx → 校验 → 对话讲解）
- 测试：6 个用例全部通过（模型序列化、PDF 解析/裁剪/图注、WPS 转换、格式校验）

**验证**
- `python -m pytest tests/ -q` → 6 passed
- 端到端：样例 PDF → prep 提取 2 图（光栅+矢量）→ 构造 content.json → 生成图文 docx → WPS 转 PDF 渲染校验通过

**已知限制**
- 扫描版 PDF（无文字层）无法提取图注/文本，需 OCR
- 图注在上方的论文、双栏复杂版面可能裁剪不准，需人工/视觉复核
- 脚本模式的 `content`/`full` 阶段需配置 API key（`config.json` 或环境变量）
