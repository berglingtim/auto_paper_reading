# 更新日志

版本规则：主版本.次版本.修订号；大更新（新功能/结构变化）本地 git 提交并记录版本号。

---

## v0.1.7（2026-08-10）补齐漏转公式 + 修复加粗嵌套

**背景**：用户反馈 `P_o^(j-1)`、`Wd ∈ R^{D×D̂}` 未渲染成公式。经扫描确认：这两处当初转换
content.json 时被遗漏，仍是带 `^` 的纯文本（并非缓存问题）；另发现 3 处加粗标记嵌套损坏
（`****CLIP** **ViT-L/14****`、`****Image-Adaptive Prompt** Learning**`，源于术语列表重叠）。

**本次改动**
- content.json 补齐：`$W_d \in \mathbb{R}^{D\times \hat{D}}$`、`$W_u \in \mathbb{R}^{\hat{D}\times D}$`、`$P_o^{(j-1)}$`
- 修复 3 处嵌套加粗标记 → 单层 `**CLIP ViT-L/14**`、`**Image-Adaptive Prompt Learning**`
- 断言校验：$ 配平（66）、$ 外无 `^`、无 `****`、33 个公式全部可解析
- 验证（视觉裁剪确认）：`W_d ∈ R^{D×D̂}`（含下标与 D 帽子）、`P_o^{(j-1)}`、`P_i^{(j)} = α^{(j)} ⊙ P_o^{(j-1)} + T^{(j)}` 均正确渲染

---

## v0.1.6（2026-08-10）修复公式渲染：移除非法 m:group + 字体统一黑色

**背景**：用户反馈"有些公式渲染有问题、有些没渲染成功"，要求用视觉探查；并要求字体全部黑色。

**根因（视觉+PDF 文字层定位）**：OMML 规范中没有 `<m:group>` 元素，WPS 直接丢弃其内容——
所有 `{...}` 分组（上下标、\frac、\sum 上下限、\left...\right 内部）整体消失，
表现为 "T∈"（缺上标）、"2||"（定界符内容丢失）、"L="（缺下标）等。

**本次改动**
- `omml.py` 解析器重构：`{...}` 组不再包装为 m:group，而是展开为父容器
  （m:e / m:num / m:den / m:sub / m:sup / oMath）的直接子元素；函数名（log 等）改用正体样式
- `tools/build_docx.js`：默认样式显式 `color: 000000`，全文档（含公式）字体统一黑色
- 验证：WPS 渲染 PDF 文字层出现 ∈/⊙/α/σ/× 等符号；视觉确认
  `T^(j) ∈ R^(2×D)`、`P_i^(j) = α^(j) ⊙ P_o^(j-1)`、`L_avg`、`p=1/m Σ σ(z_k)` 等公式渲染完整；
  30 个 OMML 注入、22 个测试全过

---

## v0.1.5（2026-08-10）公式改为 WPS 原生渲染：LaTeX → OMML

**背景**：用户要求公式用 WPS 渲染（此前是 `α^(j)` 这类纯文本，WPS 不会渲染成公式）。

**本次改动**
- 新增 `src/auto_paper_reading/omml.py`：LaTeX → OMML（Office Math）转换器，支持上下标、\frac、\sum/\prod/\int、\sqrt、\left...\right、希腊字母、\mathbb、函数与常用符号
- `tools/build_docx.js`：`$...$` 公式提取为占位 run
- `cli.py`：docx 生成后把占位 run 替换为 OMML 元素（python-docx 层完成，不调用任何 Office 软件）
- `output/iapl/IAPL/content.json`：30 处公式改为 `$...$` LaTeX（Eq 1/2/6、熵损失、形状符号等）
- 新增 `tests/test_omml.py`（10 个用例）
- `SKILL.md`：content.json 增加 `$...$` 公式语法说明

**验证**：30 个 OMML 公式注入成功、占位清零、python-docx 树内 30 个 m:oMath 结构正确、格式审计 0 问题、78 段 4 图完整。测试共 22 个用例通过（含修复 `skip_ws` 空串死循环导致的 pytest 挂起；basetemp 配置移到 conftest）。

---

## v0.1.4（2026-08-10）docx 格式规范：黑体/宋体 + Times New Roman 斜体 + 三级标题

**背景**：用户明确生成 docx 的格式要求。

**本次改动**
- `tools/build_docx.js` 全面改造：
  - 西文/数字一律 **Times New Roman 斜体**（按字符类别切分 run，中文保持正体）
  - 一级标题黑体三号(16pt)、二级黑体四号(14pt)、三级黑体小四(12pt)、正文宋体小四(12pt)、图注 10.5pt
  - 正文专业术语支持 `**...**` 加粗标记；`{"type":"heading","level":2|3}` 二级/三级标题块
  - 修复封面标题 run 失效 bug（对象展开改显式 allBold 参数）
- `output/iapl/IAPL/content.json`：47 处专业术语加粗 + 二级/三级标题（方法部分按组件拆二级，变换过程按步骤拆三级）
- `SKILL.md`：content.json 新增 heading 块与加粗标记说明 + 格式规范表
- 验证：全文档 2197 个 run 审计 0 问题（全部 TNR、西文全斜体、字号分布正确）；78 段、5 图结构校验通过

---

## v0.1.3（2026-08-09）修改范围锁定工作区 + WPS 全部改为显式 opt-in

**背景**：用户明确"能修改的范围仅限本工作区"；且此前 360 对 kimi.exe 驱动 wps.exe 的行为误报（自动化办公软件属安全软件敏感行为）。

**本次改动**
- `parser/__init__.py`：`.doc/.docx` 解析默认拒绝调用 WPS，必须显式 `--allow-wps` 才走 `kwpsconvert.exe word2pdf` 无头转换，否则直接报错并提示
- `cli.py`：新增 `--allow-wps` 参数（默认关闭）；docx 阶段默认只做结构化校验（不调用 Office）
- `pytest.ini`：`basetemp` 收进工作区 `.pytest_tmp/`，测试不再写系统临时目录
- `SKILL.md`：写入"修改范围红线"（仅工作区）+ WPS 显式 opt-in 说明
- 测试：新增 `test_docx_requires_allow_wps`，共 12 个用例全部通过

**当前所有 WPS 调用点均为用户显式触发**：`.doc/.docx` 输入转换（--allow-wps）、预览渲染（--verify）。

---

## v0.1.2（2026-08-09）WPS 使用红线：默认流程不再调用 WPS

**背景**：用户反馈"别让 WPS 打开它不该打开的东西"——此前 `wps.exe /t` GUI 转换测试会真的在 WPS 里打开文档，且生成 docx 后自动调 WPS 转 PDF 渲染。

**本次改动**
- `cli.py`：docx 阶段默认只做**结构化校验**（python-docx + zipfile，不依赖任何 Office 软件）；视觉渲染预览改为显式 `--verify` 才执行
- 明确 WPS 使用红线：全流程仅允许无头的 `kwpsconvert.exe word2pdf`（不弹窗），用于 `.doc/.docx` 输入转换与显式 `--verify`；绝不调用 `wps.exe` 打开 GUI、绝不自动处理输出文件
- `SKILL.md`：Step 5 校验方式与 WPS 红线写入工作流文档

---

## v0.1.1（2026-08-09）修复配图裁剪 + 交付首篇论文讲解

**本次改动**
- `figures.py` 重写配图裁剪：
  - 用 `get_images() + get_image_rects()` 取图片真实放置位置，支持旋转/镜像图片（原 bbox 倒置导致漏检，如 IAPL 的 Figure 4 架构图）
  - 光栅区域按垂直/水平相邻合并（同一 Figure 的子图行自动合并，如 IAPL 的 Figure 2 t-SNE 三联图）
  - 矢量图（流程图/架构图）按图注定位 + 绘图对象并集裁剪，解决无嵌入图片的流程图漏检（如 IAPL 的 Figure 1/3）
  - 过滤压住正文文字的误框、越界矩形、整页背景图；每页缓存绘图对象避免重复解析
- `cli.py`：输出文件名净化（防路径逃逸）、node 子进程加 180s 超时、UTF-8 控制台输出
- 新增 `tests/test_figures.py`（bbox 规范化、区域合并、图注正则等纯函数测试）
- 测试：11 个用例全部通过

**交付**
- 首次完成真实论文讲解验收：`papers/IAPL.pdf`（AI 生成图像检测，arXiv 2508.01603）
  → 解析提取 6 张配图 → 视觉筛选 4 张关键图 → 撰写四部分图文讲解 →
  生成 `output/iapl/IAPL/讲解_....docx`（7 页，图文混排）→ WPS 转 PDF 渲染校验通过

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
