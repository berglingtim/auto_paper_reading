---
name: auto-paper-reading
description: >
  当用户要求"讲解 / 精读 / 解读 / 复盘一篇论文"，或提供 .pdf/.docx/.doc 论文文件、
  希望输出图文结合的讲解 Word 文档时使用。工作流：解析论文 → 裁剪关键流程图 →
  图文结合撰写四部分讲解 → 生成 docx → 校验排版 → 对话中讲解。
  触发词：讲论文、读论文、论文讲解、paper reading、帮我读懂这篇论文 等。
---

# auto_paper_reading 论文讲解工作流

把一篇论文（`.pdf` / `.docx` / `.doc`）变成一份**图文结合的中文讲解 docx**，
并在对话里把论文讲给用户听（验收标准：用户满意）。

## 执行总览

```
输入论文
  ↓ ① 解析与裁剪      python run.py <paper> --stage prep --out output/<论文名>/
  ↓ ② 视觉分析        mcp__kimi-ai-hybrid__vision 逐张看候选图，选定关键图
  ↓ ③ 撰写讲解        output/<论文名>/content.json（四部分 + 图文结合）
  ↓ ④ 生成 docx       node tools/build_docx.js <content.json> <输出.docx>
  ↓ ⑤ 校验排版        渲染 PDF/图片检查
  ↓ ⑥ 交付与记录      对话中讲解 + 更新 LOGS.md + git 提交（大更新给版本号）
```

## Step 0 准备论文

1. 确认论文路径。若在项目目录外，先复制到 `papers/`（例如 `papers/xxx.pdf`）。
2. 若输入是 `.doc` / `.docx`，无需手工转换，`run.py` 会用 WPS 自动转 PDF。

## Step 1 解析与裁剪

```bash
# PDF 输入：无需任何额外授权
python run.py papers/xxx.pdf --stage prep --out output/xxx

# .doc / .docx 输入：需要显式 --allow-wps（调用 WPS 无头转换 kwpsconvert.exe word2pdf）
python run.py papers/xxx.docx --stage prep --out output/xxx --allow-wps
```

⚠️ **修改范围红线**：本工作流只允许修改/读写 `C:\Users\Tim\Desktop\auto_paper_reading` 工作区内的内容；
不触碰 360、注册表、系统设置、工作区外任何文件。360 等安全软件对"办公软件自动化"可能误报，
是否放行由用户自行在安全软件界面决定，本工作流不代为操作。

产物：
- `output/xxx/paper.json`：标题、作者、期刊/会议、摘要、全文、配图清单（图注、页码、坐标）
- `output/xxx/figures/fig_XX_pN.png`：裁剪出的候选配图（含光栅图和按图注定位的矢量图区域）

**检查点**：
- 查看 `paper.json` 的 `title` / `journal` / `year`。若为空或明显不对，从 `text` 或 PDF 首页补正
  （标题通常在首页前几行；期刊/会议名可搜 "arXiv"、"IEEE Transactions"、"Proceedings of"、
  "ICLR/ICML/CVPR/NeurIPS" 等关键字）。
- 若一篇论文的图极少或缺失，可能是扫描版 PDF（无文字层），需向用户说明并询问是否 OCR。

## Step 2 视觉分析（必须调用 kimi-ai-hybrid 的 vision 工具）

⚠️ **本环境（DeepSeek 侧）不原生看图，必须用 `mcp__kimi-ai-hybrid__vision`**。

对 `output/xxx/figures/` 下的每张候选图，依次调用：

```
mcp__kimi-ai-hybrid__vision, image_source = <figures/fig_XX.png 的绝对路径>
```

记录每次返回的 `场景分类 / 关键对象 / 可见文字 / 意图推测 / 建议动作`。

**选图规则**（从候选图里选出 1~4 张讲解必配的关键图）：
- 优先选：整体架构图（architecture）、方法流程图（flowchart）、关键模块示意图
  （数据流、注意力机制、损失/训练流程等）—— 与"二、方法"和"三、变换过程"强相关。
- 一般不要：实验结果对比图（通常用文字总结即可）、照片、截图、无关插图。
- 若某张关键图裁剪不理想（截断、串入邻图、缺块），用下面的片段**重新裁剪**后替换：

```python
import fitz
doc = fitz.open("papers/xxx.pdf")
page = doc[页码 - 1]                      # 1-based 页码
clip = fitz.Rect(x0, y0, x1, y1)          # 在 paper.json 的 bbox 基础上微调
pix = page.get_pixmap(matrix=fitz.Matrix(200/72, 200/72), clip=clip, alpha=False)
pix.save("output/xxx/figures/fig_XX_pN.png")
```

## Step 3 撰写讲解内容 content.json

在 `output/xxx/content.json` 写入结构化讲解（**路径必须可被 docx 脚本读取，建议绝对路径**）。

### content.json 格式

```json
{
  "title": "论文标题",
  "meta": { "journal": "CVPR 2024", "year": "2024", "authors": "作者列表", "source": "papers/xxx.pdf" },
  "figures": [
    { "id": "fig_02", "path": "output/xxx/figures/fig_02_p2.png",
      "caption": "Figure 2: ...", "width_in": 6.0, "height_in": 3.8 }
  ],
  "sections": [
    { "title": "一、方法灵感和发表期刊", "blocks": [
        { "type": "text", "text": "第一段……\n第二段……" },
        { "type": "heading", "level": 2, "text": "二级小标题" },
        { "type": "figure", "fig_id": "fig_02", "note": "围绕这张图的讲解文字……" }
    ]},
    { "title": "二、方法", "blocks": [ ... ] },
    { "title": "三、输入内容的变换过程", "blocks": [ ... ] },
    { "title": "四、创新点、可以借鉴的经验", "blocks": [ ... ] }
  ]
}
```

- `width_in` / `height_in` 从 `paper.json` 拷贝；需要调整大小时改这两个值即可。
- `fig_id` 必须与 `figures` 里的 `id` 对应。
- 文本中用 `**术语**` 标记加粗（仅用于专业名词/需强调处，如 **IAPL**、**CLIP**）。
- 文本中用 `$...$` 包裹 **LaTeX 公式**：生成 docx 时自动转为 OMML 公式对象，由 **WPS 打开时原生渲染**（非图片、非纯文本）。支持上下标、\frac、\sum/\prod、\sqrt、\left...\right、希腊字母、\mathbb、\log 等常用子集（见 `src/auto_paper_reading/omml.py`）。示例：`$P_i^{(j)} = \alpha^{(j)} \odot P_o^{(j-1)} + T^{(j)}$`。
- `{"type":"heading","level":2|3,"text":"..."}` 可在部分内加二级/三级小标题。

### 生成 docx 的格式规范（自动套用，写作时无需关心）

| 元素 | 字体 | 字号 |
|---|---|---|
| 封面标题 | 黑体（西文 Times New Roman 斜体） | 18pt |
| 一级标题 | 黑体 | 三号 16pt |
| 二级标题 | 黑体 | 四号 14pt |
| 三级标题 | 黑体 | 小四 12pt |
| 正文 | 宋体 | 小四 12pt |
| 图注/说明 | 宋体 | 10.5pt |

- **英语字母和数字一律 Times New Roman 斜体**（中文正体不受影响，由排版脚本自动切分）
- 正文中的专业名词用 `**...**` 标记加粗

### 讲解写作规范（质量核心）

**一、方法灵感和发表期刊**
- 痛点/动机：作者在解决什么问题、现有方法差在哪；
- 灵感来源：借鉴了哪些前作/思想（引用原文线索）；若有创新点承接关系，讲清演进；
- 发表信息：期刊/会议名 + 年份；可补充该会议/期刊的级别（如 CCF-A/B、中科院分区），并说明依据。

**二、方法（必须图文结合）**
- 分模块讲解：每个模块的输入→处理→输出；核心公式用文字解释含义（不必抄公式）；
- 在关键位置插入 `{"type":"figure","fig_id":...,"note":...}`，note 里**逐块、逐箭头**
  讲清图里画了什么：每个方框的作用、箭头代表的数据流向、标注的含义；
- 讲清损失函数、训练策略、推理流程。

**三、输入内容的变换过程（数据流视角，最重要）**
像追踪数据一样讲：
- **每一步变换**：输入（如 3×H×W 图像）如何被处理——尺寸、通道数、分辨率、特征图
  形状的变化；token/序列长度变化；归一化、padding、patch 化等；
- **每步学习**：哪些模块/参数在训练中被更新，学到了什么表征，是否有预训练/冻结/微调；
- **注意力机制的变化**（若有）：Q/K/V 来源与形状、attention map 的含义与维度、
  权重如何随层/训练演化、多头/稀疏/因果等细节；
- 结合流程图逐模块走完整条数据流，让读者能"跟着箭头走一遍"。

**四、创新点、可以借鉴的经验**
- 创新点 2~5 条，相对已有工作的核心差异；
- 可借鉴经验：训练技巧、工程实现、数据组织、损失设计等，对做研究/工程的人有迁移价值；
- 客观标注论文未明确说明的细节（"论文未明确说明"），不要编造。

**通用要求**：简体中文；术语保留英文（首次出现给中文释义）；基于原文，不编造；引用图时
描述与图中内容一致（以 Step 2 的 vision 结果为准，看错图宁可少讲）。

## Step 4 生成 docx

```bash
node tools/build_docx.js output/xxx/content.json "output/xxx/讲解_<标题>.docx"
```

## Step 5 校验排版

**默认只做结构化校验（不调用任何 Office 软件）**：

```bash
python run.py papers/xxx.pdf --stage docx --out output/xxx
# 输出 [check] 结构校验通过：N 段、M 表、K 张嵌入图片
```

需要**视觉渲染预览**（把 docx 转 PDF 渲染成图片人工查看排版）时，显式加 `--verify`：

```bash
python run.py papers/xxx.pdf --stage docx --out output/xxx --verify
# 渲染 output/xxx/verify/page_*.png，用 Read 逐页查看
```

⚠️ **WPS 使用红线**：
- 全流程只允许调用 **无头的 `kwpsconvert.exe word2pdf`**（命令行转换，不弹窗），
  仅用于两处：`.doc/.docx` 输入转换、显式 `--verify` 的预览渲染。
- **绝不**调用 `wps.exe` 打开 GUI、绝不自动用 WPS 打开/处理输出文件。
- 生成 docx 后由用户自己在 WPS 中打开查看（项目不做任何 WPS 文件关联操作）。

用 Read 检查预览图时重点看：中文无乱码、图片完整不超版心、四部分结构清晰。
发现问题 → 修改 content.json → 重新生成。

## Step 6 交付与记录

1. **对话中讲解**：按四部分结构，用口语化但专业的方式把论文讲给用户听，
   说明配图内容与讲解的对应关系（验收标准：用户满意）。
2. 把输出 docx 的路径告知用户（用户用 WPS 打开）。
3. 更新 `LOGS.md`（日期、版本号 vX.Y.Z、本次改动）。
4. **大更新**（新增功能/结构变化）执行 `git add -A && git commit`，版本号记录在 LOGS.md。
   小修补（文案、单处 bug）可只在 LOGS.md 追加记录。

## 常见问题

| 现象 | 处理 |
|---|---|
| `.doc/.docx` 报"需要 --allow-wps" | 该格式必须经 WPS 无头转换才能解析；确认后显式加 `--allow-wps` 重跑 |
| `.doc/.docx` 转换失败 | 确认 WPS 已安装；或设置环境变量 `WPS_CONVERT` 指向 `kwpsconvert.exe`（仅无头转换，不弹窗） |
| 需要渲染预览图 | `python run.py ... --stage docx --verify`（显式开启，才调用 WPS 无头转换） |
| 安全软件误报 | 360 等对"办公软件自动化"可能报警（误报），是否放行由用户在安全软件界面自行决定 |
| 扫描版 PDF（无文字层） | 提取不到图注/文本，向用户说明并询问是否需要 OCR |
| 长论文（>50 页） | 讲解聚焦方法/变换过程，正文截断即可；必要时分段阅读再写 |
| 裁剪出的图很乱 | 按 Step 2 的重裁剪片段手动框选 |
| vision 工具不可用 | 无法可靠看图，向用户说明并降级：仅依据图注+上下文文字讲解，图仍嵌入 |
| 需要 API 自动生成 | 配置 `config.json`（文本 DeepSeek + 视觉 Kimi），跑 `python run.py ... --stage full --text-provider deepseek --vision-provider kimi` |
