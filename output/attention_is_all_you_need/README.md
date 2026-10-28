# Attention Is All You Need · 完整双语案例 / Complete bilingual example

[返回中文首页](../../README.md) · [English project documentation](../../README.en.md)

这是使用 auto_paper_reading 生成并逐页检查的完整论文讲解，随 **v0.4.1** 发布。先读 PDF 即可了解项目的实际输出；Word 文件保留可编辑的文字、公式和原生表格。

These complete explanations were generated with auto_paper_reading, checked page by page, and published with **v0.4.1**. Read the PDF to see the finished output, or download the Word document to edit its text, equations, and native tables.

| 语言 / Language | PDF 在线阅读 / Read online | Word 下载 / Download |
|:---:|:---:|:---:|
| 中文 · 14 页 | [中文版 PDF](Attention_Is_All_You_Need_zh.pdf) | [中文版 DOCX](Attention_Is_All_You_Need_zh.docx?raw=true) |
| English · 15 pages | [English PDF](Attention_Is_All_You_Need_en.pdf) | [English DOCX](Attention_Is_All_You_Need_en.docx?raw=true) |

这些 v0.4.1 历史 PDF 保留 WPS 渲染快照。**v0.5.0 起项目默认使用免费开源 LibreOffice**；不需要 WPS。相同 DOCX 在不同字体和转换器下可能重新分页，须重新检查。These v0.4.1 PDFs preserve their original WPS rendering. **Starting with v0.5.0, the project defaults to free, open-source LibreOffice** and does not require WPS. Different fonts and renderers can change pagination and require fresh inspection.

## 内容 / Contents

两种语言覆盖相同内容，按各自篇幅独立分页。Both versions cover the same material, with pagination adjusted for each language:

1. **摘要与核心符号 / Abstract and core notation** — 论文背景、翻译场景、WMT 2014 测试结果，以及关键符号的含义和维度。Background, translation scenarios, WMT 2014 test results, and important symbols and shapes.
2. **基础知识与动机 / Prerequisites and motivation** — 编码器—解码器、注意力、位置编码、残差连接、LayerNorm 和 BLEU。Encoder-decoder models, attention, positional encodings, residual connections, LayerNorm, and BLEU.
3. **方法与 baseline / Method and baseline** — 对比 ConvS2S 与 Transformer 的核心机制，解释架构、公式和训练。Compare ConvS2S and Transformer mechanisms, then explain the architecture, equations, and training.
4. **数据如何变换 / How the input changes** — 从 token、嵌入和多头张量到编码、解码与输出。Trace tokens, embeddings, and multi-head tensors through encoding, decoding, and generation.
5. **结果与解决范围 / Results and scope** — 解读原文结果及消融；结合后续论文，用“证据 → 推断”分析低资源翻译、同传、长文本计算与有效信息利用。Interpret results and ablations, then use evidence → inference to examine low-resource translation, simultaneous translation, long-context computation, and effective use of information.

每份包含 **5 张原文图表、3 张原生三线表、8 条参考文献**。原生表格为黑白色，顶底线 1.5 pt、表头线 0.75 pt，单元格水平与垂直居中；原文截图保留原貌。Each report contains **5 original figures/table excerpts, 3 native three-line tables, and 8 references**. Native tables use black-and-white styling, 1.5 pt outer horizontal rules, a 0.75 pt header rule, and centered cell contents. Source excerpts retain their original appearance.

## 来源与检查 / Sources and verification

- 主论文 / Main paper: Vaswani et al., **Attention Is All You Need**, NIPS 2017（现称 / now NeurIPS），[arXiv:1706.03762v7](https://arxiv.org/abs/1706.03762v7)。讲解中的原文页码、图表和数值对应此版本。Paper page numbers, figures, tables, and results refer to this version.
- Baseline: Gehring et al., [Convolutional Sequence to Sequence Learning](https://proceedings.mlr.press/v70/gehring17a.html), ICML 2017。
- 后续文献检索截至 **2026-10-28**，具体链接与章节定位见报告末尾。Later research was checked through **2026-10-28**; the reports provide links and precise locations. Later-model evaluations are distinguished from the original Transformer's experiments.
- v7 的摘要与表 2 将英法 big 结果写为 **41.8 BLEU**，§6.1 的一处正文为 **41.0**；两份讲解均保留这个版本内差异。Both reports retain this discrepancy between the abstract/Table 2 and one sentence in Section 6.1.
- 两份 DOCX 各有 **88 个原生 OMML 数学对象**，自动公式审计均为 **0 问题**；已通过 WPS 无头渲染并检查中文全部 14 页、英文全部 15 页。Each DOCX contains **88 native OMML math objects**, with **0 issues** in the automated equation audit. All 14 Chinese pages and 15 English pages were visually reviewed after headless WPS rendering.

这里的 PDF 是对应 Word 的渲染快照。需要了解生成方式，可阅读[中文工作流](../../SKILL.md)或 [English workflow](../../SKILL.en.md)；需要最小内容格式示例，可阅读 [examples](../../examples/README.md)。The PDFs are rendering snapshots of the matching Word files. The workflow documents explain how to generate a report; `examples/` contains minimal format examples.
