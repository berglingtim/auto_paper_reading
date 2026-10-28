# auto_paper_reading

[![简体中文](docs/images/lang-zh.svg)](README.md) [![English](docs/images/lang-en.svg)](README.en.md)

**English** · [简体中文（默认 / default）](README.md)

[Releases and downloads](https://github.com/berglingtim/auto_paper_reading/releases) · [MIT license](LICENSE) · [Software citation](CITATION.cff)

A **paper-reading toolkit for AI agents**. Open this repository in a workspace with a vision-capable agent, such as Claude Code, Codex, Qwen Code, or Kimi Code, and ask it to explain a paper. The agent follows the workflow to **find the paper → parse it and crop figures → inspect the figures → investigate baselines and field challenges → write an illustrated explanation → build and check a DOCX report**.

Reports can be written in **Chinese or English**. Chinese remains the default. The toolkit **does not call an LLM API or require an API key**: the agent does the research, visual analysis, and writing. The scripts handle parsing, cropping, typesetting, and checks.

## Read a complete example: Attention Is All You Need

See the finished bilingual reports in `output` before installing anything:

| Language | Read online | Download editable Word |
|:---:|:---:|:---:|
| 中文 · 14 pages | [Read PDF](output/attention_is_all_you_need/Attention_Is_All_You_Need_zh.pdf) | [Download DOCX](output/attention_is_all_you_need/Attention_Is_All_You_Need_zh.docx?raw=true) |
| English · 15 pages | [Read PDF](output/attention_is_all_you_need/Attention_Is_All_You_Need_en.pdf) | [Download DOCX](output/attention_is_all_you_need/Attention_Is_All_You_Need_en.docx?raw=true) |

Both reports include an abstract, core notation, a ConvS2S baseline comparison, the complete method and data flow, original figures and tables, and scenario analysis using **evidence → inference** from subsequent research. Equations and every rendered page have been checked. See the [case study notes and sources](output/attention_is_all_you_need/README.md).

These complete reports are published with **v0.4.1**. The shorter files in `examples/` demonstrate the content format and layout.

## What's new in v0.5.0

- Word input conversion and `--verify` previews now default to **LibreOffice headless**, which is free and open source. No WPS, Microsoft Word, or paid conversion service is required.
- Each conversion uses private staging and an isolated profile. A new PDF is validated before replacing the output; failures preserve the previous PDF. Failed requested previews return a nonzero exit status while retaining the generated DOCX.
- WPS is available only through `--pdf-backend wps` or the legacy `--allow-wps` alias. There is no automatic fallback to WPS.

## What's new in v0.4.0

- Chinese and English documentation, with language buttons at the top. The GitHub landing page remains Chinese.
- An [English agent workflow](SKILL.en.md), alongside the [Chinese workflow](SKILL.md).
- Report language selection through `content.json.language` or `--language zh|en`. Generated headings, notation labels, caption prefixes, dates, equation numbers, and filename prefixes follow that selection.
- Matching [Chinese](examples/zh/content.json) and [English](examples/en/content.json) layout examples. See [how to build them](examples/README.md).

The report standards introduced in v0.3.0 remain: an opening abstract and concise notation table, baseline mechanism comparisons, evidence-based analysis of scope and unresolved problems, and centered monochrome three-line tables.

## Quick start

1. Clone the repository and open it in your agent's workspace. Use `SKILL.md` as the skill entry point; it links to the English workflow.
2. Install the local dependencies:

   ```bash
   python -m pip install -r requirements.txt
   npm install
   ```

3. Ask the agent: **“Explain Attention Is All You Need in English and produce an illustrated Word report.”** You can also provide a local PDF, DOCX, or DOC file.
4. The agent researches the paper, authors the report, and runs the build and verification steps. English output is named `Explanation_<paper title>.docx`.

Requirements: Python 3.10+, Node.js, and an agent that can search the web and inspect images. For Word input conversion and final visual verification, see [rendering support](#rendering-support).

To request both versions: **“Create separate Chinese and English reports for this paper.”** The agent should author each version in its target language and use separate output directories.

## Language selection and CLI

```bash
# Parse a paper. Actual working directory: output/en/paper/
python run.py papers/paper.pdf --stage prep --out output/en --language en

# The agent now writes output/en/paper/content.json in English,
# including "language": "en", an abstract, notation, and the body.

# Build the report and render it with LibreOffice for inspection.
python run.py papers/paper.pdf --stage docx --out output/en --language en --verify

# Check the exact report that will be delivered.
python tools/verify_math.py "output/en/paper/Explanation_Paper Title.docx"
```

The working directory is always `<--out>/<input filename without extension>/`. Use the actual generated filename in the final command. For Chinese reports, use `zh` and a separate output root such as `output/zh`.

During the DOCX stage, language precedence is **`--language` → `content.json.language` → `zh`**. Accepted values are `zh` and `en`; unsupported values are rejected. The prep stage only uses the flag for CLI messages; the agent must still set the language when authoring `content.json`.

**The language setting does not translate authored text.** The agent must write the title, abstract, notation explanations, section titles, body, captions, and table cells in the requested language. The scripts localize generated labels and numbering. No translation service or model API is invoked. Existing content files without a language field retain Chinese behavior.

## What the report contains

After the title and publication details, every new report starts with:

- **Abstract:** background, application scenarios, the problem addressed, the central method, and concrete dataset/split/metric results. Include comparable baseline values and precise paper locations when available.
- **Notation:** only important, recurring, paper-specific, or ambiguous symbols. Explain meaning, type/shape, role, and source/scope. Define simple temporary variables where they appear; do not invent unreported dimensions.

The body then covers five parts:

1. **Prerequisites** — explain each concept, why it works, a concrete example, and its role in this paper.
2. **Motivation and publication** — problem, inspiration, prior work, venue, and year.
3. **Method** — compare the baseline's core mechanism with the paper's mechanism when reliable sources exist, then explain the modules with figures.
4. **How the input changes** — trace shapes, representations, parameter updates, attention, and outputs through the entire pipeline.
5. **Contributions and transferable lessons** — interpret original result tables, explain what the paper actually solves, identify remaining problems and applicable scenarios, and extract lessons with their conditions.

Before writing part 5, the agent must search relevant recent papers and benchmarks for concrete field problems and application scenarios. It then compares those findings with the main paper's assumptions, data, and experiments. Each insight follows **evidence → inference**, citing both the external research and the main paper and recording the search date.

Distinguish an unresolved problem from an untested scenario, and a historical contribution from a gap addressed by later work. Missing experiments do not establish failure. If current research cannot be checked, state the actual evidence boundary rather than claiming a verified current gap.

Baseline research distinguishes a **methodological predecessor** from an **experimental comparator**. Explain the baseline's core, this paper's core, and the concrete change. If reliable information cannot be found, skip the comparison. Do not recursively turn the task into a literature survey. Compare numerical improvements only under comparable evaluation protocols.

## DOCX formatting

| Element | Typeface | Size |
|---|---|---|
| Title | Times New Roman, bold | 18 pt |
| Level 1 heading | Times New Roman | 16 pt |
| Level 2 heading | Times New Roman | 14 pt |
| Level 3 heading | Times New Roman | 12 pt |
| Body | Times New Roman | 12 pt |
| Metadata, captions, figure notes | Times New Roman | 10.5 pt |
| Table text | Times New Roman | 9 pt |
| References section | Times New Roman | 7.5 pt |

Chinese text uses SimSun for body text and SimHei for headings. Latin letters and digits use upright Times New Roman; variables inside equations follow native math styling.

- All generated text, including headings and equations, is black. The page layout remains A4 for both languages.
- English heading numbers are **1 / 1.1 / 1.1.1**; Chinese numbers are **一 / 1.1 / 1.1.1**. Abstract and notation headings are unnumbered. Supply heading text without manual numbers.
- All native tables use white backgrounds and three black horizontal rules: **1.5 pt** top/bottom borders and a **0.75 pt** header separator. There are no vertical rules or other row separators. Tables and all cell content are centered horizontally; cell content is also centered vertically. Original paper table images retain their original appearance.
- Body paragraphs and figure notes are justified with a first-line indent equal to twice their font size (24 pt for 12 pt text). Titles and captions are centered. Headings, equations, and captions have no first-line indent.
- Inline `$...$` expressions become editable **OMML equations**. Display equations are centered, with right-aligned numbers: `(1), (2), …` in English and `（1）, （2）, …` in Chinese.
- Use `**term**` for emphasis. Preserve original paper result tables as high-resolution crops and explain how to read them.

## Content format

New reports use top-level `language`, `abstract`, `symbols`, `figures`, and `sections`. The language defaults to `zh`. Each notation item has `symbol` and `meaning`; `shape`, `role`, and `source` provide context.

Native tables and display equations can be authored as blocks:

```json
{
  "type": "table",
  "headers": ["Method", "Core mechanism"],
  "rows": [["Baseline", "Verified prior mechanism"], ["This paper", "Verified change"]],
  "column_weights": [1, 3]
}
```

```json
{"type": "equation", "latex": "y = Wx + b"}
```

Table cells support line breaks, bold text, and inline math. Header rows repeat across pages; rows do not split. Put display equations outside tables. Escape LaTeX backslashes in JSON. See [the full writing workflow](SKILL.en.md) and [runnable examples](examples/README.md).

Images scale proportionally, normally up to 4.5 inches high and 6.2 inches wide. Use `layout.max_figure_height_in` / `max_figure_width_in` globally, or `max_height_in` / `max_width_in` on individual figures or figure blocks. Section/block `page_break_before: true` and `{"type":"page_break"}` support deliberate pagination.

## Rendering support

**PDF parsing and DOCX generation do not need an office application.** Word input conversion and `--verify` previews default to **LibreOffice**, a free, open-source local application.

On Windows or macOS, install [LibreOffice](https://www.libreoffice.org/download/), including Writer and Math. On Ubuntu/Debian:

```bash
sudo apt install libreoffice-writer libreoffice-math fonts-noto-cjk fonts-liberation
```

The tool searches PATH and common installation directories. To override discovery, set `LIBREOFFICE_PATH` to the executable:

```powershell
# Windows PowerShell; normally discovered automatically
$env:LIBREOFFICE_PATH = 'C:\Program Files\LibreOffice\program\soffice.com'
```

```bash
# macOS override; Linux typically uses /usr/bin/libreoffice
export LIBREOFFICE_PATH=/Applications/LibreOffice.app/Contents/MacOS/soffice

# DOC/DOCX input uses LibreOffice by default
python run.py papers/paper.docx --stage prep --out output/en --language en
# Previews also default to LibreOffice
python run.py papers/paper.pdf --stage docx --out output/en --language en --verify
# Optional installed Windows WPS converter
python run.py papers/paper.pdf --stage docx --out output/en --language en --verify --pdf-backend wps
```

`--pdf-backend libreoffice|wps` selects the converter for both Word input and previews. The legacy `--allow-wps` flag is an alias for choosing WPS; it cannot be combined with `--pdf-backend`. Set `WPS_CONVERT` to the optional WPS converter if discovery fails. No backend launches a GUI or changes file associations; there is no automatic WPS fallback.

LibreOffice supports Windows, macOS, and Linux. This release was tested on **Windows with real DOC/DOCX inputs and both complete example reports**; actual macOS/Linux rendering has not yet been validated. Install the fonts used by your reports. Font substitutions and different layout engines can change line breaks, formula spacing, and pagination, so inspect every page after conversion. The published historical case PDFs retain their original renderer, documented in the [case notes](output/attention_is_all_you_need/README.md).

Without a converter, DOCX generation and structural math checks remain available, but visual verification is incomplete. A failed requested preview returns a nonzero exit status and preserves the generated DOCX.

## Required checks before delivery

The Python build injects OMML and performs strict math checks. Directly running the Node builder produces an intermediate file and is not a complete delivery workflow. Formula failures block successful generation; a matching `.math_audit.json` records the findings.

Render with `--verify`, inspect **every page**, review `verify/layout_audit.json` (including its `pdf_backend`), and run `tools/verify_math.py` against the exact DOCX being delivered. The PDF must match the DOCX filename and be at least as recent. Failed rendering means verification is incomplete even if the DOCX exists.

Check subscripts/superscripts, fractions, table borders and centering, figure readability, heading placement, and whitespace. Structural checks cannot establish mathematical meaning or good visual layout. Correct problems, regenerate, and inspect again. Literal underscores in filenames or code identifiers require narrowly scoped `math_review_exceptions`; equations cannot be exempted.

## Repository layout

```text
README.md / README.en.md       Chinese and English documentation
SKILL.md / SKILL.en.md         Agent workflows
examples/                     Matching bilingual content examples
docs/images/                  README illustrations and language buttons
run.py                        CLI entry point: prep / docx
src/auto_paper_reading/        Parsing, cropping, content, OMML, and checks
tools/build_docx.js            DOCX layout builder
tools/verify_math.py           Delivery-time equation checks
papers/                       Local input papers (ignored)
output/                       Public Attention case study; other generated output is ignored
tests/                        Functional and regression tests
requirements.txt              Python dependencies
package.json                  Node dependency: docx
```

Run the tests with `python -m pytest tests/ -q` after installing pytest. Backend smoke tests run when their converter is installed and otherwise skip; the other conversion tests do not require office software. Dependencies are PyMuPDF, python-docx, Pillow, lxml, and Node's `docx` package; no LLM SDK or API key is required.

## License and citation

Original project code and documentation are licensed under the [MIT license](LICENSE). Paper figures and other third-party material in the examples retain their respective copyrights and licenses; sources are listed in the case study notes and report references.

Use **Cite this repository** in the GitHub sidebar to obtain a software citation, based on [CITATION.cff](CITATION.cff). This cites the toolkit; cite the original papers separately when using their findings.
