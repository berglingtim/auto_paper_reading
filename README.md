# auto_paper_reading

输入一篇论文（`.pdf` / `.docx` / `.doc`），自动输出**图文结合的中文讲解 docx**（格式规范见下），
由 Agent（SKILL.md 工作流）或脚本（LLM API）两种方式驱动。

## 讲解内容结构（五部分，三级编号标题 1 / 1.1 / 1.1.1）

1. **基础知识讲解** —— 前置知识拆成小点逐个讲（CLIP、ViT、注意力、Adapter/LoRA、
   Prompt Learning、测试时自适应、高频信号与 DCT、任务设定等），每点注明本文用法
2. **方法灵感和发表期刊** —— 发表信息、动机、灵感来源
3. **方法** —— 分模块讲解，配关键流程图/架构图，三级小标题细分
4. **输入内容的变换过程** —— 数据流视角：每一步如何变换、每步学什么、注意力如何变化
5. **创新点、可以借鉴的经验** —— 核心创新点 + 实验结果（**直接调用论文原表**逐表讲解）+ 可借鉴经验

## 生成 docx 的格式规范

| 元素 | 字体 | 字号 |
|---|---|---|
| 封面标题 | 黑体（西文 Times New Roman 斜体） | 18pt |
| 一级标题 | 黑体 | 三号 16pt |
| 二级标题 | 黑体 | 四号 14pt |
| 三级标题 | 黑体 | 小四 12pt |
| 正文 | 宋体 | 小四 12pt |
| 图注/说明 | 宋体 | 10.5pt |

- **英语字母和数字一律 Times New Roman 斜体**（中文正体，排版脚本自动切分）
- **全文档字体颜色统一黑色**（含标题/正文/公式/图注，禁止主题蓝）
- 标题**自动编号**（一级 1、二级 1.1、三级 1.1.1），content.json 只写标题文字
- 正文专业名词用 `**术语**` 加粗；公式用 `$LaTeX$` 包裹，自动转为 OMML 由 **WPS 原生渲染**
- 实验结果直接裁剪论文原表（Table）高清嵌入 + 逐表讲解

## 两种使用方式

### A. Agent Skill 方式（推荐，零配置）

在 Kimi Code 中说"讲解一下 papers/xxx.pdf"，Agent 按 `SKILL.md` 工作流执行：
解析裁剪 → kimi-ai-hybrid 视觉分析选图 → 撰写讲解 → 生成 docx → **渲染自检** → 对话中讲解。
无需 API key。

### B. Python 脚本方式（需要 API key）

```bash
# 阶段 1：解析 + 裁剪图片
python run.py papers/xxx.pdf --stage prep --out output/xxx

# 阶段 2+3：视觉筛选 + LLM 生成讲解 + 生成 docx（全流程）
python run.py papers/xxx.pdf --stage full \
  --out output/xxx --text-provider deepseek --vision-provider kimi
```

配置 `config.json`（复制 `config.example.json` 填 key），或设置环境变量
`DEEPSEEK_API_KEY` / `MOONSHOT_API_KEY`。文本默认 DeepSeek，视觉默认 Kimi。

### 交付自检（硬性要求）

```bash
python run.py papers/xxx.pdf --stage docx --out output/xxx --verify   # WPS 无头渲染预览
python tools/verify_math.py                                           # 公式渲染自检
```
再对公式密集区域视觉抽验；全部通过才交付。输出 docx 被占用（如正被 WPS 打开）时自动写 `_v2` 文件。

## 目录结构

```
├── AGENTS.md / SKILL.md        # 项目说明与 Agent 讲解工作流
├── run.py                      # CLI 入口
├── src/auto_paper_reading/     # 核心 Python 包
│   ├── parser/                 #   解析层（pdf/docx/doc 统一为 PaperDocument）
│   ├── figures.py              #   配图提取与裁剪（光栅图 + 图注定位矢量图）
│   ├── omml.py                 #   LaTeX → OMML 公式转换（WPS 原生渲染）
│   ├── llm.py / explain.py     #   LLM 客户端抽象 / 讲解内容生成
│   ├── docx_content.py         #   content.json 中间格式
│   └── cli.py                  #   命令行编排（prep/content/docx/full）
├── tools/
│   ├── build_docx.js           # docx-js 排版（字体/字号/编号/公式占位）
│   └── verify_math.py          # 公式渲染交付自检
├── papers/                     # 论文输入目录
├── output/                     # 讲解输出目录（每篇论文一个子目录）
├── tests/                      # 22 个单元测试
├── config.example.json / requirements.txt / pytest.ini / package.json
└── LOGS.md                     # 更新日志（版本号）
```

## 依赖

- Python 3.10+：`pymupdf`、`python-docx`、`pillow`、`openai`、`lxml`
- Node.js：`docx`（docx-js 排版）
- WPS Office：仅 `.doc/.docx → PDF` 输入转换与 `--verify` 预览渲染
  （无头 `kwpsconvert word2pdf`，需显式 `--allow-wps` / `--verify` 才调用）

## 版本记录

见 `LOGS.md`。
