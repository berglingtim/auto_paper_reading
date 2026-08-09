# auto_paper_reading

输入一篇论文（`.pdf` / `.docx` / `.doc`），自动输出**图文结合的中文讲解 docx**。

## 讲解内容结构（四部分）

1. **方法灵感和发表期刊** —— 动机、灵感来源、发表期刊/会议及级别
2. **方法** —— 分模块技术细节，配关键流程图/架构图逐块讲解（图文结合）
3. **输入内容的变换过程** —— 数据流视角：每一步如何变换、每步学习什么、注意力机制如何变化
4. **创新点、可以借鉴的经验** —— 核心创新点 + 可迁移的研究/工程经验

## 两种使用方式

### A. Agent Skill 方式（推荐，零配置）

在 Kimi Code 中说"讲解一下 papers/xxx.pdf"，Agent 会按 `SKILL.md` 工作流执行：
解析裁剪 → kimi-ai-hybrid 视觉分析选图 → 撰写讲解 → 生成 docx → 校验 → 对话中讲解。
无需任何 API key。

### B. Python 脚本方式（需要 API key）

```bash
# 阶段 1：解析 + 裁剪图片
python run.py papers/xxx.pdf --stage prep --out output/xxx

# 阶段 2+3：视觉筛选 + LLM 生成讲解 + 生成 docx（全流程）
python run.py papers/xxx.pdf --stage full \
  --out output/xxx --text-provider deepseek --vision-provider kimi
```

配置 `config.json`（复制 `config.example.json`，填入 API key），或设置环境变量
`DEEPSEEK_API_KEY` / `MOONSHOT_API_KEY`。文本模型默认 DeepSeek，视觉模型默认 Kimi。

## 目录结构

```
├── SKILL.md                    # Agent 讲解工作流（主交付）
├── run.py                      # CLI 入口
├── src/auto_paper_reading/     # 核心 Python 包
│   ├── parser/                 #   解析层（pdf/docx/doc 统一为 PaperDocument）
│   ├── figures.py              #   配图提取与裁剪（光栅图 + 图注定位矢量图）
│   ├── llm.py                  #   LLM 客户端抽象（DeepSeek/Kimi/OpenAI）
│   ├── explain.py              #   讲解内容生成（脚本模式）
│   ├── docx_content.py         #   content.json 中间格式
│   └── cli.py                  #   命令行编排
├── tools/build_docx.js         # docx-js 排版脚本（docx skill 生成方式）
├── papers/                     # 论文输入目录
├── output/                     # 讲解输出目录
└── LOGS.md                     # 更新日志（版本号）
```

## 依赖

- Python 3.10+：`pymupdf`、`python-docx`、`pillow`、`openai`
- Node.js：`docx`（`tools/build_docx.js` 用）
- WPS Office（`.doc/.docx → PDF` 转换，`kwpsconvert.exe`）

## 版本记录

见 `LOGS.md`。
