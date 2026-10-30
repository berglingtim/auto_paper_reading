# Agensi listing copy

Copy each section into its corresponding listing field. Adapter version: 0.6.0.
External toolkit target: v0.6.0. Pricing is selected separately by the creator.

## Name

Auto Paper Reading — Illustrated Word Reports

## Summary

Turn a research paper into an illustrated, editable Word explanation in Chinese or English, with core notation, baseline comparisons, concrete results, and evidence-based insights. Requires a local toolkit.

## Description

Understand how a paper works, what its results show, and where its contribution stops.

Auto Paper Reading guides your AI agent from a paper title, PDF, DOC, or DOCX to an illustrated Word report. It combines original figures, editable equations, and clear explanations of the method and data flow.

Each complete report includes:

- An opening abstract covering the background, application, problem solved, and concrete dataset results.
- A compact notation table for the symbols that matter.
- Prerequisites, motivation, publication context, and step-by-step mechanisms.
- Comparisons between verified baselines and the paper's core ideas.
- A trace of the input through the model, including shapes and learning behavior where supported.
- Original result-table excerpts and explanations of comparable results.
- Evidence → inference analysis of remaining problems, informed by relevant research and the paper's actual assumptions.

Reports use editable Word equations, black-and-white three-line tables, centered table cells, and consistent heading numbering. Ask for Chinese, English, or two separate versions. Chinese is the default when no language is specified.

**How it works**

Your agent researches the paper, examines its figures, and writes the explanation. A separately installed [open-source toolkit](https://github.com/berglingtim/auto_paper_reading) handles parsing, figure crops, Word layout, and equation checks. Free LibreOffice provides Word input conversion and PDF previews. The workflow then calls for a page-by-page visual review.

This listing delivers the agent workflow and supporting instructions. It does not bundle Python, Node.js, LibreOffice, the toolkit source tree, or a hosted execution environment. The toolkit makes no LLM API calls and requires no separate model API key; your agent's own account and usage costs still apply.

**Before using it**

Use a local agent with terminal and file access, web research, and image viewing. Install auto_paper_reading v0.6.0 and its dependencies first, or ask your agent to help with setup. A browser-only chatbot without these tools cannot complete the workflow.

Read the [full bilingual Attention Is All You Need example](https://github.com/berglingtim/auto_paper_reading/tree/v0.6.0/output/attention_is_all_you_need) to judge the depth and layout before starting.

## See it in action

**A real project request, translated from Chinese:**

“Use the project to generate a new version of Attention Is All You Need so I can see the result.”

Follow-up requests asked for the complete revised Word explanation, then separate Chinese and English examples.

**Full results from the public GitHub project:**

- [English report — PDF, 15 pages](https://github.com/berglingtim/auto_paper_reading/blob/v0.6.0/output/attention_is_all_you_need/Attention_Is_All_You_Need_en.pdf)
- [English report — editable Word](https://github.com/berglingtim/auto_paper_reading/raw/refs/tags/v0.6.0/output/attention_is_all_you_need/Attention_Is_All_You_Need_en.docx)
- [Chinese report — PDF, 14 pages](https://github.com/berglingtim/auto_paper_reading/blob/v0.6.0/output/attention_is_all_you_need/Attention_Is_All_You_Need_zh.pdf)
- [Chinese report — editable Word](https://github.com/berglingtim/auto_paper_reading/raw/refs/tags/v0.6.0/output/attention_is_all_you_need/Attention_Is_All_You_Need_zh.docx)

The reports explain the Transformer architecture, compare its mechanisms with ConvS2S, and trace tokens through embeddings, attention heads, encoding, decoding, and output generation. Each begins with an abstract and core notation, then covers the background, method, data flow, results, and remaining application scope.

Each document contains five original figure/table excerpts, three native tables, and 88 editable math objects. The final analysis uses evidence and inference to discuss low-resource translation, simultaneous translation, long-context computation, and effective use of information. Sources and evidence locations appear in the reports.

These are complete historical toolkit outputs, originally published with v0.4.1, not demonstrations of a live Agensi integration. Their PDF snapshots used WPS. The adapter targets v0.6.0, which defaults to free LibreOffice; fonts and renderers can change pagination. The [case notes](https://github.com/berglingtim/auto_paper_reading/blob/v0.6.0/output/attention_is_all_you_need/README.md) document the sources and original checks.

## Compatibility note

Requires a local agent with terminal, filesystem, web research, and image viewing; auto_paper_reading v0.6.0; Python 3.10+ with project dependencies; Node.js with npm dependencies; and LibreOffice for DOC/DOCX input conversion and PDF/page verification. The toolkit has been exercised on Windows. Actual macOS/Linux rendering and live Agensi loading have not yet been validated.

## Categories

Research & Analysis

Education & Learning

Productivity

## Tags

research papers, paper reading, academic research, literature review, machine learning, Word reports, DOCX, editable equations, Chinese, English

## Use cases

- Understand a paper before implementing its method.
- Prepare an illustrated explanation for a research group or class.
- Compare a method's core ideas with its verified baselines.
- Examine dataset results and the boundaries of an application claim.
- Create separate Chinese and English reading notes.

## Permissions and access

Reads the selected paper and local toolkit files; writes parsed material, figure crops, report content, Word documents, PDF previews, and audit files within the chosen working area. Runs local Python, Node.js, and LibreOffice commands. Uses web access for open-access papers, original references, and relevant research. Dependency installation, if requested, downloads from the public project and package providers. No GitHub write access or paper upload to a cloud converter is needed.

## Limitations

- The external toolkit and runtime dependencies must be installed separately.
- Scanned PDFs require separate OCR; complex layouts may need figure recropping.
- Research depth depends on source availability and the host agent's capabilities.
- Baseline details are omitted when reliable sources cannot be found.
- Formula audits assist review; they do not establish mathematical or factual correctness.
- Missing LibreOffice or image viewing prevents a fully visually checked delivery.
- Changing fonts or rendering engines can change pagination.
- Local execution needs read/write access to the host's temporary directory and permission to run the converter.
- This adapter has local validation only; Agensi review and live loading remain to be confirmed.

## FAQ

**Do I need WPS, Microsoft Word, or a paid PDF conversion API?**

No. The default conversion backend is free LibreOffice. WPS remains an optional explicit backend in the external toolkit.

**Does it need an LLM API key?**

The toolkit does not call an LLM API. Research, writing, and visual inspection use your current agent and its available tools.

**Can it generate English reports?**

Yes. Request English explicitly, or ask for separate Chinese and English versions. The agent authors each version; a language flag alone does not translate the text.

**Is the underlying project open source?**

Yes. The project's original code and documentation, and this adapter's original instructions, use MIT. The public repository remains available on GitHub. Dependencies and source-paper materials retain their own licenses; PyMuPDF has separate AGPL/commercial licensing.

**Will it judge whether a paper is correct?**

It provides source-grounded explanations and evidence-based analysis. It is not a guarantee of correctness, a peer review, or a replacement for reading the original evidence.

## Documentation URL

https://github.com/berglingtim/auto_paper_reading/blob/v0.6.0/README.en.md
