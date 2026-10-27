---
name: auto-paper-reading
description: >
  Read and explain a research paper from a PDF, DOCX, DOC, or paper title,
  and produce an illustrated Chinese or English Word report. Use for requests
  to read, explain, or closely analyze a paper, including finding the paper,
  interpreting figures, comparing baselines, and assessing its contribution
  and remaining scope using relevant research. No LLM API is called.
---

# auto_paper_reading workflow

[简体中文](SKILL.md) | [English](SKILL.en.md)

Turn a research paper into an illustrated DOCX explanation and explain it to the user. The current agent performs web research, visual inspection, and writing. Scripts only parse, crop, typeset, and check. The skill entry point is `SKILL.md`; this file provides the equivalent English workflow.

## Language and output locations

- Follow the user's requested report language. If none is specified, use Chinese, even when the source paper is English. Reading this English workflow does not by itself select English output.
- Set top-level `"language": "en"` or `"language": "zh"` in `content.json`. Author the title, abstract, notation explanations, section titles, body, captions, and tables in that language. Keep paper titles, algorithm names, quotations, and original figure text in their source language where appropriate.
- DOCX language precedence is `--language` → `content.json.language` → `zh`. The prep-stage flag changes CLI messages only; still set the language when authoring content. Unsupported language values fail.
- The renderer translates generated labels, not authored prose. It does not call a translation service. Do not merely change `language` on a Chinese report and present it as an English translation.
- For two versions, author separate content files in separate output directories. For input `papers/paper.pdf` and `--out output/en`, the working directory is **`output/en/paper/`**. The CLI always appends the input filename without its extension to `--out`.
- English reports use `Abstract`, `Notation`, `1 / 1.1 / 1.1.1`, equation numbers `(1)`, and the filename prefix `Explanation_`. Chinese reports retain `摘要`, `符号表`, `一 / 1.1 / 1.1.1`, `（1）`, and `讲解_`.

Both languages follow the same source, reasoning, figure, table, and verification standards below.

## Workflow

1. Locate and download the paper, unless an appropriate local copy is available.
2. Parse it and crop candidate figures.
3. Inspect the figures and select or recrop the useful ones.
4. Identify baselines and compare their core mechanisms when sources can be verified.
5. Research relevant field problems and scenarios before writing the final body section.
6. Author the abstract, notation, and five-part explanation in `content.json`.
7. Build the DOCX, render and inspect every page, verify equations, then deliver.

## Step 0 — Obtain the paper

For a local file outside the workspace, copy it into `papers/` before processing. If only a title is supplied, search for the title plus arXiv, CVF open access, or PDF. Prefer the publisher's open-access copy, arXiv, an author-hosted copy, or a verified open-access link. Download within the workspace.

Verify that the download is a PDF with a usable text layer, not an HTML error page:

```bash
python -c "import fitz; d=fitz.open('papers/paper.pdf'); print(len(d), 'pages'); print(d[0].get_text()[:200])"
```

Retry another source if needed; report the limitation if no suitable copy is available. Scanned PDFs need separate OCR handling; do not pretend their text has been parsed.

## Step 1 — Parse and crop

```bash
python run.py papers/paper.pdf --stage prep --out output/en --language en

# Word input requires explicit headless WPS permission via this flag.
python run.py papers/paper.docx --stage prep --out output/en --language en --allow-wps
```

Outputs include `output/en/paper/paper.json` (metadata, text, and figure coordinates) and `output/en/paper/figures/` (candidate crops).

Check the title, venue, year, and authors against the first page and source text; correct missing or clearly wrong metadata. A lack of figures may reflect a scanned document or extraction failure.

Keep modifications within the repository workspace. Do not change the registry, file associations, security software, or system settings. If security software blocks office automation, leave its controls to the user and report the actual failure.

## Step 2 — Inspect figures

Use the agent's own image-viewing capability; this toolkit calls no vision API. Inspect candidates individually and record figure type, visible objects/text, and relevance.

Select roughly 1–4 key architecture, workflow, attention, module, or training diagrams for the method and data-flow explanations. Avoid unrelated images. Result-table crops are additional evidence for the results section.

If extraction cuts a figure apart, mixes columns, or omits labels, inspect the full PDF page and recrop by coordinates instead of joining fragments blindly:

```python
import fitz
doc = fitz.open("papers/paper.pdf")
page = doc[1]  # Example only: choose the verified zero-based page index.
clip = fitz.Rect(x0, y0, x1, y1)  # Set from the inspected page.
pix = page.get_pixmap(matrix=fitz.Matrix(200 / 72, 200 / 72), clip=clip, alpha=False)
pix.save("output/en/paper/figures/method.png")
```

Preserve complete annotations and aspect ratios. If visual inspection is unavailable, disclose that limitation and base explanations only on captions and surrounding text; do not invent unseen details.

## Step 2.5 — Find baselines and compare mechanisms

1. Read the main paper's method, experimental setup, result tables, and ablations. Distinguish a **methodological predecessor** from an **experimental comparator**. A backbone, highly cited reference, or best-performing competitor is not automatically the method's starting point.
2. Select a small number of baselines that explain the paper's actual changes. Follow its reference numbers to original papers, author project pages, or official code. Read the relevant method sections when available.
3. If reliable sources cannot be found, use only what the main paper clearly establishes and skip missing details. If no baseline can be verified, state that briefly and move on. Do not guess, demand extra material merely to fill this section, or expand recursively into a literature survey.
4. Explain **baseline core → this paper's core → concrete change**: input processing, learning, outputs, what was added/replaced/removed, what was inherited, and what is new. A short native table can summarize the comparison; explain mechanisms in prose.
5. Record baseline title, reference number in the main paper, verified URL, and supporting section/page. Distinguish the main paper's description from a claim confirmed in the baseline's original text. An abstract alone does not support detailed training or algorithm reconstruction.
6. Compare numbers only under comparable dataset/split, metric, training-data, and model-size conditions. Prefer controlled comparisons in the main paper. Do not subtract results from incompatible protocols or confuse an original result with a later reproduction.

## Step 2.6 — Research field challenges and the paper's actual scope

**Complete this step before writing part 5.** Identify concrete problems and scenarios in relevant research, then determine which part the paper solves, under what conditions, and what remains. Generic lists of efficiency, robustness, or generalization concerns are insufficient.

1. Define the search around the paper's task, input assumptions, and plausible applications. Search recent relevant primary papers and benchmarks using task/scenario terms with challenge, limitation, evaluation, or generalization. Reviews can identify leads, but substantive claims should return to primary evidence. Choose a time window appropriate to the field.
2. For a few directly relevant problems, read the actual scenario, observed failure or difficulty, conditions, and evidence. Check subsequent research before calling an older open problem a current gap.
3. Pair each field problem with the main paper's task definition, assumptions, supervision, training/test data, experiments, and discussion. Explain the specific mismatch or remaining stage of the application. Include only problems related to the paper's aim or a reasonable application.
4. Distinguish **solved/improved**, **not solved by this paper**, and **not evaluated by this paper**. Missing evaluation supports “not yet validated in scenario B,” not “fails in B.” If later work addresses the issue, say this paper did not cover it and later work extends the scope.
5. Record search date, paper title, year/version, URL, and supporting section/table/page. Claims about field challenges need external citations; claims about the main paper's capabilities need main-paper evidence. Separate historical contribution from later findings rather than attributing modern claims to an older paper.
6. Narrow conclusions when evidence is insufficient. If web research is unavailable, disclose that the current-field check is incomplete and retain only source-supported scope analysis. The baseline step's permission to skip unavailable details does not replace this step.

## Step 3 — Author content.json

Save English content at `output/en/paper/content.json` for the commands above. Prefer figure paths relative to that file, such as `figures/method.png`. Use the [English layout example](examples/en/content.json) to inspect working syntax; it is a formatting fixture, not a completed research report.

```json
{
  "language": "en",
  "title": "Paper title",
  "meta": {"journal": "Verified venue", "year": "2026", "authors": "Verified authors"},
  "abstract": "Explain the background, application, problem, method, and verified dataset results with source locations.",
  "symbols": [
    {"symbol": "$X$", "meaning": "Input features", "shape": "$N \\times d$", "role": "Feature sequence", "source": "Verified section or equation"}
  ],
  "figures": [],
  "sections": [
    {"title": "Prerequisites", "blocks": [{"type": "text", "text": "Explain the required concepts."}]},
    {"title": "Motivation and publication", "blocks": [{"type": "text", "text": "State the verified context."}]},
    {"title": "Method", "blocks": [{"type": "heading", "level": 2, "text": "Core mechanism"}]},
    {"title": "How the input changes", "blocks": [{"type": "text", "text": "Trace inputs, operations, learning, and outputs."}]},
    {"title": "Contributions and transferable lessons", "blocks": [
      {"type": "heading", "level": 2, "text": "What the paper actually solves"},
      {"type": "text", "text": "Explain the demonstrated contribution and its conditions."},
      {"type": "heading", "level": 2, "text": "Remaining problems and application scope"},
      {"type": "text", "text": "Evidence: cite the external field problem and the main paper's assumptions or results.\nInference: explain what is covered, what remains, and which scenarios are merely untested."}
    ]}
  ]
}
```

Replace illustrative descriptions with researched content. Add the selected figures and original result-table crops; an empty figure list in the syntax example is not permission to omit figures from a full report.

### Content and layout contract

- New reports require `abstract` and `symbols`; they appear before the body without consuming heading numbers. Do not repeat them in `sections`. Legacy files missing these fields still build.
- Write a nonempty explanatory abstract in the target language. Do not copy the source abstract. Typically use 120–180 English words or 150–250 Chinese characters, extending when needed for concrete results.
- Notation items require `symbol` and `meaning`. Optional `shape`, `role`, and `source` explain type/dimensions, computational role, and evidence/scope. Do not infer unreported dimensions; use “Not specified in the paper.” Use `[]` when no symbols need a separate table.
- Include core, repeated, distinctive, or ambiguous symbols. Explain simple indices, temporary quantities, constants, and auxiliary dimensions locally. A short symbol such as a central query matrix can still deserve a row. Explain new symbols again at first use when needed for readability.
- Math uses `$...$` for inline expressions. JSON requires escaped backslashes. A display equation uses `{"type":"equation","latex":"y = Wx + b"}` without delimiters or a manual number. `$$...$$` also creates a numbered display equation. Numbers run continuously across sections.
- Use `{"type":"heading","level":2,"text":"..."}` or level 3 for subsections. Supply text without numbering. Use the hierarchy to separate modules and data-flow steps.
- Native tables use `type`, nonempty string `headers`, and `rows` of matching width. Cells contain strings or numbers. Optional `column_weights` must be positive and match the columns. Cells support line breaks, `**bold**`, and inline math; put display equations outside tables.
- **All native tables are black-and-white three-line tables:** 1.5 pt top/bottom lines, 0.75 pt header separator, no vertical or other internal rules, white fill, black text. Center the table and all cell content horizontally and vertically, including headers and explanatory columns. Headers repeat across pages; avoid fixed row heights. Preserve original paper table screenshots unchanged.
- Copy figure dimensions from `paper.json` to preserve aspect ratio. Adjust proportional display limits with `max_height_in` / `max_width_in`, not by changing only one original dimension. Defaults are 4.5 inches high and 6.2 inches wide; the hard height limit is 8 inches. Readability takes precedence over minimizing pages.
- Global limits live under `layout.max_figure_height_in` / `max_figure_width_in`; precedence is figure block → figure entry → global layout → default. A block references a matching figure ID through `fig_id` and explains it through `note`.
- A section or block may set `page_break_before: true`; a `page_break` block breaks before the next actual content. Do not pad with empty paragraphs.
- Keep body text and figure notes justified, with a first-line indent equal to twice the font size. Titles and captions are centered. Headings, equations, and captions are not indented. A4 size is shared by both languages.
- Latin text/digits are upright Times New Roman; Chinese body/headings use SimSun/SimHei. Sizes: title 18 pt; heading levels 16/14/12 pt; body 12 pt; metadata/captions/notes 10.5 pt; tables 9 pt; references 7.5 pt. Only math variables follow italic math styling. All generated text is black, including built-in heading styles.
- `**term**` provides emphasis. Equations must become editable OMML through the Python stage. The Node output alone still contains intermediate placeholders and must not be delivered.

### Writing standards

**Abstract and notation come first**, followed by five body parts. Report exact dataset names/splits, metrics and directions, values, and source locations. Include comparable baseline values where available. Distinguish percentage points from relative percentages. If there are no quantitative experiments, describe the actual evaluation evidence instead of inventing values.

**1. Prerequisites.** Recommended, especially for unfamiliar mechanisms. Give each concept its own subsection. Explain what it is in 2–4 sentences, why the mechanism works, and a concrete numerical or situational example. State how this paper uses it.

**2. Motivation and publication.** Explain the problem, the shortcomings motivating the study, inspiration from prior work, and the verified venue/year. Any optional venue ranking needs an explicit reliable basis.

**3. Method.** Begin with the verified baseline comparison when available. Explain each module's input → processing → output, important equations, losses, training, and inference. Interleave key figures and explain their boxes, arrows, and annotations individually. Do not substitute a caption paraphrase for a mechanism explanation.

**4. How the input changes.** Trace the entire data flow: dimensions, channels, resolution, features, token counts, normalization, padding, and patching where relevant. Identify updated versus frozen parameters, pretraining/fine-tuning, and learned representations. For attention, trace query/key/value origins and shapes, weight meanings, and multi-head/sparse/causal behavior. Do not invent measured changes across training or layers.

**5. Contributions and transferable lessons.** Explain roughly 2–5 substantive innovations relative to prior work. Crop original result tables at about 300 dpi, preserving headers, method rows, and original highlights. Embed them as figures and explain column groups, the paper's values, comparable baselines, and what the results support.

State what the paper actually solves or improves, for which inputs, supervision, data, and applications. Then organize remaining issues by the concrete scenarios researched in Step 2.6. For each issue:

- **Evidence:** identify the externally documented field problem and the main paper's assumptions, design, evaluation coverage, or results, with separate citations.
- **Inference:** explain which portion the paper addresses, what remains, and what conditions or capabilities a target application would need. Missing evaluation means unverified scope, not demonstrated failure.

Prioritize research problems and application boundaries. Discuss cost or parameter tradeoffs when they matter to those scenarios. Distinguish the paper's measurements, later research findings, and the explanation's inference. Small single-run differences do not establish statistical significance or invalidate a mechanism. Extract reusable training, engineering, data, or loss-design lessons with the conditions that must be retained or tested.

Write in the target language, expand acronyms at first use in English, and define English terms in Chinese reports. Match every figure description to what was actually inspected. Use specific evidence-based insights instead of repetitive defensive phrases or invented limitations.

## Steps 4–5 — Build and inspect

```bash
python run.py papers/paper.pdf --stage docx --out output/en --language en --verify
python tools/verify_math.py "output/en/paper/Explanation_Paper Title.docx"
```

Use the exact generated filename. Without `--verify`, the build only performs structural and math checks. The current preview/Word-input backend is Windows WPS, using **headless `kwpsconvert.exe word2pdf`** or its compatible `wpscli.exe` entry point. The workflow must not launch `wps.exe`, open the GUI, or change file associations. Only explicit `--allow-wps` and `--verify` enable these two conversion uses. Other office applications, international WPS builds, and macOS/Linux rendering have not been validated.

If no supported converter is available, report that visual verification remains incomplete. A generated DOCX or a successful structural check does not establish a visually verified deliverable. Check warnings even when the CLI returns a generated path.

For every delivery, render previews, read `verify/layout_audit.json`, and inspect every page. Verify front-matter order, target-language labels and numbering, table borders/centering/repeated headers, complete figures, readable text, and black headings/body/math. Nonfinal pages with more than 28% bottom whitespace or 20% internal whitespace trigger review; these are diagnostics, not automatic layout decisions. A short final page does not need to be filled artificially.

If a figure moves to the next page leaving excessive whitespace: inspect/crop unnecessary margins, reduce proportional display limits when readable (often 3–4.5 inches high), reposition its adjacent explanation, or break at a natural subsection boundary. Keep captions with figures and headings with following text. Do not force every section onto a new page or shrink dense tables beyond readability. Regenerate and inspect all affected pages; retain reasonable whitespace when necessary for readability.

## Step 6 — Verify evidence and deliver

Before delivery, check the abstract's concrete results, concise notation, baseline classification and comparison, and part 5's external research with search dates and source locations. Verify the distinction between unresolved, untested, and later-addressed problems. Scripts cannot validate factual claims or reasoning.

**Equation verification is mandatory:**

1. Render the exact DOCX being delivered. Its matching PDF must have the same stem and be no older than the DOCX; do not select an arbitrary version from a directory.
2. Run `tools/verify_math.py` with that DOCX path and clear all issues in its `.math_audit.json`.
3. Inspect every `_` and `^`: compare source LaTeX, OMML base/subscript/superscript structure, and visible placement. Check all formulas, including table cells, captions, headings, and notes. One correct script does not validate another.
4. Literal filename/code underscores require exact full-paragraph `math_review_exceptions` entries with a reason, for example `{"text":"File model_weights.bin","reason":"Literal filename, not a math variable"}`. No broad wildcard exemptions and no exemption for residual markers inside equations.
5. Inspect every page and zoom into dense formulas. Check function scripts, combined sub/superscripts, fractions, sum limits, delimiters, and inline math against the paper. A PDF text layer cannot prove correct placement or meaning.
6. Correct errors in content or the converter, regenerate, and verify again before declaring the report checked.

Explain the paper conversationally in the requested language, beginning with its summary and then the five-part structure. Give a link to the final DOCX and state any actual unresolved verification limitation.

## Troubleshooting

| Symptom | Action |
|---|---|
| Word input needs `--allow-wps` | Use the explicit flag for the supported headless conversion workflow. |
| Converter not found | Verify the installed Windows converter or set `WPS_CONVERT` to its actual path. Do not substitute GUI automation. |
| Security software blocks conversion | Report the error; do not operate its settings. |
| Scanned PDF | Explain the missing text layer and discuss OCR if needed. |
| Poor crops | Inspect the full page and recrop the actual figure region. |
| Long paper | Read relevant sections in manageable chunks and focus the explanation on method/data flow; do not discard evidence needed for claims. |
| Malformed JSON | Check quoting and doubled LaTeX backslashes. |
| English labels with Chinese prose | Have the agent author/translate and verify the prose; the language flag does not translate it. |
| Report saved but preview failed | Deliver only with the actual verification status; resolve rendering before claiming full visual checks. |
