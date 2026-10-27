# 双语排版示例 / Bilingual layout examples

[简体中文首页](../README.md) · [English home](../README.en.md)

这两份示例使用相同内容结构，演示摘要、核心符号表、三级编号、原生公式与黑白三线表。
它们是**排版示例**，不是完整论文讲解，不含虚构的论文发表信息或评测数据。
正式报告仍需按 SKILL 核实来源、查 baseline 和领域问题，并嵌入原文关键图表。

These matching fixtures demonstrate front matter, notation, three heading levels, editable equations,
and monochrome three-line tables. They are **layout examples**, not complete paper explanations.
Real reports still require source verification, baseline and field research, and original paper figures/tables.

| 语言 / Language | 内容 / Content | 默认输出 / Default output |
|---|---|---|
| 简体中文 | [zh/content.json](zh/content.json) | `output/examples/zh/讲解_排版示例.docx` |
| English | [en/content.json](en/content.json) | `output/examples/en/Explanation_Layout Example.docx` |

从仓库根目录运行，先按首页安装 Python 和 Node 依赖。
Run from the repository root after installing the Python and Node dependencies listed in the README.

```bash
# 生成两份 DOCX，包含 OMML 注入和数学检查；无需办公软件
# Build both DOCX files with OMML injection and math checks; no office app required
python examples/build.py

# 使用已支持的 Windows WPS 无头后端生成预览
# Render previews using the supported headless Windows WPS backend
python examples/build.py --verify

# 检查本次输出的确切文件 / Check the exact generated files
python tools/verify_math.py "output/examples/zh/讲解_排版示例.docx"
python tools/verify_math.py "output/examples/en/Explanation_Layout Example.docx"
```

可用 `--out output/my-examples` 指定其他输出位置。生成文件保存在忽略目录 `output/`。
`--verify` 之后仍须逐页看图；仅生成 DOCX 或通过结构检查不代表视觉检查完成。

Use `--out output/my-examples` for another output root. Generated files stay in ignored `output/`.
After `--verify`, inspect every preview page. A generated DOCX or passing structural checks alone
does not establish correct visual layout.
