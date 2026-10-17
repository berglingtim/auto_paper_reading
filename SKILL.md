---
name: auto-paper-reading
description: >
  当用户要求"讲解 / 精读 / 解读 / 复盘一篇论文"，或提供 .pdf/.docx/.doc 论文文件，
  或只给出论文题目希望自动搜索下载，并输出图文结合的讲解 Word 文档时使用。
  工作流：搜索下载论文 → 解析裁剪关键图 → 视觉分析选图 → 图文结合撰写五部分讲解
  → 生成 docx → 校验排版 → 对话中讲解。
  触发词：讲论文、读论文、论文讲解、paper reading、帮我读懂这篇论文 等。
---

# auto_paper_reading 论文讲解工作流

把一篇论文（`.pdf` / `.docx` / `.doc`）变成一份**图文结合的中文讲解 docx**，
并在对话里把论文讲给用户听（验收标准：用户满意）。
本工具**不调用任何 LLM API**：搜索下载、看图选图、撰写讲解全部由当前 Agent
（需具备联网检索与读图能力）亲自完成；脚本只负责解析、裁剪与排版。

## 执行总览

```
输入（论文题目或本地文件）
  ↓ ⓪ 搜索与下载      联网检索论文，下载到 papers/（本地已有文件则跳过）
  ↓ ① 解析与裁剪      python run.py <paper> --stage prep --out output/<论文名>/
  ↓ ② 视觉分析        用 Agent 自身的读图能力逐张看候选图，选定关键图
  ↓ ③ 撰写讲解        output/<论文名>/content.json（五部分 + 图文结合）
  ↓ ④ 生成 docx       node tools/build_docx.js <content.json> <输出.docx>
  ↓ ⑤ 校验排版        渲染 PDF/图片检查
  ↓ ⑥ 交付            对话中讲解 + 告知 docx 路径（用户用 WPS 打开）
```

## Step 0 搜索并准备论文

**场景 A：用户给了本地文件** —— 若文件在项目目录外，先复制到 `papers/`
（例如 `papers/xxx.pdf`）。

**场景 B：用户只给论文题目** —— 用联网检索找到论文并下载：

1. 用当前 Agent 的联网检索能力，以「论文标题 + arXiv / CVF open access / PDF」检索。
2. 优先选择可直接下载的开放获取 PDF：
   - CVF（CVPR/ICCV 等）：`https://openaccess.thecvf.com/content/CVPR2025/papers/<作者>_<标题>_CVPR_2025_paper.pdf`
   - arXiv：`https://arxiv.org/pdf/<论文id>`
   - 也可先经 Semantic Scholar 的开放接口查询 openAccessPdf 直链。
3. 下载（仅写入工作区内）：
   ```bash
   curl -sL -o papers/<论文名>.pdf "<PDF直链>"
   ```
4. **下载后必须验证**（不是 HTML 错误页、且有文字层）：
   ```bash
   python -c "import fitz; d=fitz.open('papers/xxx.pdf'); print(len(d),'pages'); print(d[0].get_text()[:200])"
   ```
   能打印出页数与正文才算成功；否则换来源重试，仍不行则向用户报告。
5. 若输入是 `.doc` / `.docx`，无需手工转换，`run.py` 会用 WPS 自动转 PDF。

## Step 1 解析与裁剪

```bash
# PDF 输入：无需任何额外授权
python run.py papers/xxx.pdf --stage prep --out output/xxx

# .doc / .docx 输入：需要显式 --allow-wps（调用 WPS 无头转换 kwpsconvert.exe word2pdf）
python run.py papers/xxx.docx --stage prep --out output/xxx --allow-wps
```

⚠️ **修改范围红线**：本工作流只允许修改/读写本仓库目录（即 Agent 当前打开的工作区）
内的内容；
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

## Step 2 视觉分析（用 Agent 自身的读图能力）

本工具**不调用任何视觉 API**：由当前 Agent 直接打开候选图查看（各 Agent 自带的
读图工具 / 多模态输入），逐张记录：图片类型（架构图/流程图/实验图表/照片/表格）、
图中关键对象与可见文字、是否属于讲解「方法」必配的关键图。

**选图规则**（从候选图里选出 1~4 张讲解必配的关键图）：
- 优先选：整体架构图（architecture）、方法流程图（flowchart）、关键模块示意图
  （数据流、注意力机制、损失/训练流程等）—— 与"方法"和"变换过程"两部分强相关。
- 一般不要：实验结果对比图（通常用文字总结即可）、照片、截图、无关插图。
- 双栏复杂版式下自动提取可能切碎或串版（如架构图被拆成碎片、表格漏检），
  此时直接渲染整页，按版面人工框选坐标重裁，不要强行拼凑碎图。

若某张关键图裁剪不理想（截断、串入邻图、缺块），用下面的片段**重新裁剪**后替换：

```python
import fitz
doc = fitz.open("papers/xxx.pdf")
page = doc[页码 - 1]                      # 1-based 页码
clip = fitz.Rect(x0, y0, x1, y1)          # 在 paper.json 的 bbox 基础上微调
pix = page.get_pixmap(matrix=fitz.Matrix(200/72, 200/72), clip=clip, alpha=False)
pix.save("output/xxx/figures/fig_XX_pN.png")
```

## Step 3 撰写讲解内容 content.json

在 `output/xxx/content.json` 写入结构化讲解（图片 `path` 建议用相对路径，如
`figures/fig_02_p2.png`，相对 content.json 所在目录解析，仓库迁移/换机器不失效）。

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
- **正文和图后讲解采用两端对齐**；封面与图注保留居中，标题保留原有标题排版。
- **公式必须独立成行并编号**：推荐使用 `{"type":"equation","latex":"y = Wx + b"}`；不写 `$` 分隔符、不手工加编号。排版器自动将公式居中，右侧按全文出现顺序标为（1）、（2）……，跨章节连续编号。
- 兼容旧正文或图后讲解中的 `$...$`，以及 `$$...$$`（可跨行）：自动拆为独立公式行，保留前后文字。新内容应把完整等式写成 equation 块；普通变量名在解释中直接写文本，避免逐个符号拆行。
- 文本中用 `**术语**` 标记加粗（仅用于专业名词/需强调处，如 **IAPL**、**CLIP**）。
- 文本中用 `$...$` 包裹 **LaTeX 公式**：生成 docx 时自动转为 OMML 公式对象，由 **WPS 打开时原生渲染**（非图片、非纯文本）。支持上下标、\frac、\sum/\prod、\sqrt、\left...\right、希腊字母、\mathbb、\log 等常用子集（见 `src/auto_paper_reading/omml.py`）。示例：`$P_i^{(j)} = \alpha^{(j)} \odot P_o^{(j-1)} + T^{(j)}$`。
- `{"type":"heading","level":2|3,"text":"..."}` 可在部分内加二级/三级小标题。**标题编号自动生成**：一级=1、二级=1.1、三级=1.1.1，content.json 中**只写标题文字、不要写编号**（写编号会重复）。
- **建议用足三级标题**（1 / 1.1 / 1.1.1）细分讲解，避免大段文字混在一起；方法部分按组件/模块拆二级、三级，变换过程按步骤拆三级。

### 生成 docx 的格式规范（自动套用，写作时无需关心）

| 元素 | 字体 | 字号 |
|---|---|---|
| 封面标题 | 黑体（西文 Times New Roman 正体） | 18pt |
| 一级标题 | 黑体 | 三号 16pt |
| 二级标题 | 黑体 | 四号 14pt |
| 三级标题 | 黑体 | 小四 12pt |
| 正文 | 宋体 | 小四 12pt |
| 图注/说明 | 宋体 | 10.5pt |
| 表格中的文字 | 宋体 | 小五 9pt |
| 参考文献 | 宋体 | 六号 7.5pt（整节匹配"参考文献/References"生效） |

- **英语字母和数字一律 Times New Roman 正体**（中文正体不受影响，由排版脚本自动切分）
- **仅公式中的变量（英语字母）采用斜体**（由 OMML 数学样式承担），其他情况不做改变
- 公式仍是可编辑的 OMML 数学对象；使用 Python 的 docx 阶段完成占位替换。直接运行 Node 排版脚本只生成中间文件，不应直接交付。
- **全文档字体颜色统一为黑色**（包括标题、正文、公式、图注、封面；禁止出现主题蓝或其他颜色——docx-js 内置标题样式自带主题蓝，生成后必须校验标题颜色为纯黑 #000000）
- 正文中的专业名词用 `**...**` 标记加粗

### 讲解写作规范（质量核心）

**结构（五部分，第一个为前置知识）**：

**零、基础知识讲解**（可选但推荐）：把论文需要的前置知识拆成"一个小点一个小点"讲解
（每点一个二级标题，如 1.1 CLIP、1.2 ViT、1.3 注意力机制、1.4 Adapter/LoRA、
1.5 Prompt Learning、1.6 测试时自适应、1.7 高频信号与 DCT、1.8 任务设定）。
**每个知识点必须包含三段**：① 概念（2-4 句讲清是什么）；② **为什么能达到这样的效果**
（机制层面的解释：对比学习为何有效、注意力为何能动态路由、冻结+适配为何省且稳等）；
③ **举个例子**（具体到数字/场景的类比或实例，避免抽象）。最后注明"本文是怎么用它的"。

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
- **实验结果部分必须直接调用论文原表**：用 pymupdf 按表格 bbox 高清裁剪（300dpi）论文的
  Table 图片（含表头与方法行，保留 Ours 高亮），作为 figure 嵌入 docx（id 如 table_1），
  并在每张表后配"怎么读这张表"的讲解（分组列结构、Ours 数值、与最强基线的差距、
  跨生成器的稳定性），而不是只写文字数字；
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
# 渲染 output/xxx/verify/page_*.png，用读图工具逐页查看
```

⚠️ **WPS 使用红线**：
- 全流程只允许调用 **无头的 `kwpsconvert.exe word2pdf`**（命令行转换，不弹窗），
  仅用于两处：`.doc/.docx` 输入转换、显式 `--verify` 的预览渲染。
- **绝不**调用 `wps.exe` 打开 GUI、绝不自动用 WPS 打开/处理输出文件。
- 生成 docx 后由用户自己在 WPS 中打开查看（项目不做任何 WPS 文件关联操作）。

用读图工具检查预览图时重点看：中文无乱码、图片完整不超版心、五部分结构清晰、**标题/正文/公式均为黑色**（不得出现蓝色等主题色）。
发现问题 → 修改 content.json → 重新生成。

## Step 6 交付

0. **交付前必须自检 LaTeX 渲染**（硬性要求）：重新生成 docx 后，必须运行
   `python run.py papers/xxx.pdf --stage docx --out output/xxx --verify` 渲染预览，
   然后**逐页核验所有公式**：
   - 跑 `python tools/verify_math.py` 自动化自检（每个公式的关键符号必须在渲染 PDF
     文字层出现；`|`/`∑` 等矢量渲染符号回退检查 docx 的 OMML 结构）；
   - 再对公式密集区域裁剪放大用视觉确认（上下标、分数、求和上下限、定界符是否完整）。
   发现渲染问题 → 修 content.json 或 omml.py → 重新生成 → 再验证，直到全部通过才交付。
1. **对话中讲解**：按五部分结构，用口语化但专业的方式把论文讲给用户听，
   说明配图内容与讲解的对应关系（验收标准：用户满意）。
2. 把输出 docx 的路径告知用户（用户用 WPS 打开）。

## 常见问题

| 现象 | 处理 |
|---|---|
| `.doc/.docx` 报"需要 --allow-wps" | 该格式必须经 WPS 无头转换才能解析；确认后显式加 `--allow-wps` 重跑 |
| `.doc/.docx` 转换失败 | 确认 WPS 已安装；或设置环境变量 `WPS_CONVERT` 指向 `kwpsconvert.exe`（仅无头转换，不弹窗） |
| 需要渲染预览图 | `python run.py ... --stage docx --verify`（显式开启，才调用 WPS 无头转换） |
| 标题出现蓝色/主题色 | 内置 Heading 样式自带主题蓝；需在 build_docx.js 中给 run 显式 `color: 000000` 并覆盖标题样式（v0.1.8 已处理，勿回退） |
| 安全软件误报 | 360 等对"办公软件自动化"可能报警（误报），是否放行由用户在安全软件界面自行决定 |
| 扫描版 PDF（无文字层） | 提取不到图注/文本，向用户说明并询问是否需要 OCR |
| 长论文（>50 页） | 讲解聚焦方法/变换过程，正文截断即可；必要时分段阅读再写 |
| 裁剪出的图很乱 | 按 Step 2 的重裁剪片段手动框选 |
| Agent 无读图能力 | 无法可靠看图，向用户说明并降级：仅依据图注+上下文文字讲解，图仍嵌入 |
| 论文找不到 PDF 直链 | 换来源（CVF open access / arXiv / Semantic Scholar），或请用户提供文件 |
| content.json 解析失败 | 多为公式 LaTeX 反斜杠未按 JSON 双重转义（`\in` 应为 `\\in`），统一检查 `$...$` 段落后重试 |
