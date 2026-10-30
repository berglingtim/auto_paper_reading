# Report content and quality contract

## Evidence before authoring

Verify the paper's title, authors, venue/year, and version. Record source URLs
and section/page/table/equation locations as you research. Prefer the original
paper, original baseline papers, official projects, and primary evaluations.
Use the host agent's web tools; do not ask for a separate model API key.

Inspect selected figures against their full PDF pages. Preserve labels, aspect
ratio, and meaningful context. Recrop incomplete or mixed-column extractions
from the actual source page. Usually 1–4 key method/data-flow figures suffice;
original result-table crops are additional evidence. Explain boxes, arrows,
and annotations individually. If image viewing is unavailable, mark that
verification incomplete and do not describe details you did not see.

For baselines, distinguish the mechanism the method develops from a competitor
included only in experiments. Follow the main paper's references to original
sources; compare inputs, transformations, learning, and outputs, then explain
what was inherited, added, removed, or replaced. Skip unavailable details
without guessing or expanding into an unrelated literature survey.

Before writing part 5, search for concrete problems and scenarios in the
relevant field. Read recent primary evidence and check whether later work
has already addressed an older limitation. Pair each issue with the main
paper's assumptions, design, training/test data, and evaluation coverage.
Record the search date and the source/version supporting each conclusion.
If current research is unavailable, say so and restrict the claim to known
source-supported scope; do not present it as a completed current-field review.

## Structure

Begin with a nonempty **abstract**, then **essential notation**, before the
numbered body. The abstract explains background, application, actual problem
solved, and concrete dataset/split/metric results. Cite source locations and
comparable baseline values when available. If there are no quantitative
experiments, describe the actual evaluation instead of inventing results.

Use `symbols` only for central, recurring, ambiguous, or paper-specific notation.
Each entry needs `symbol` and `meaning`; `shape`, `role`, and `source` are optional.
Explain simple indices and temporary variables beside their first use. An empty
array is appropriate if no notation needs a separate table.

The five body parts:

1. **Prerequisites.** Explain the concepts needed to understand the mechanism,
   with concrete examples and how the paper uses each concept.
2. **Motivation and publication.** Explain the task, prior shortcomings,
   inspiration, and verified publication context.
3. **Method.** Present verified baseline comparisons, then each module's
   input → operation → output, equations, losses, training and inference.
   Integrate selected figures where they explain the mechanism.
4. **How the input changes.** Trace data and representation changes, dimensions,
   learned/frozen parameters, and attention/query/key/value origins where
   relevant. Separate architectural transformations from measured learning
   behavior; do not invent the latter.
5. **Contributions, results, and remaining problems.** Explain the substantive
   changes and results, what is actually solved, what remains, and reusable
   lessons with their conditions. Preserve original numerical result tables
   as clear crops; explain comparable rows, metrics, and protocol differences.

For each remaining problem, write:

- **Evidence:** the externally documented field problem plus separately cited
  evidence about this paper's design, assumptions, or evaluation.
- **Inference:** which part this paper addresses, what still needs solving,
  and which applications require additional capabilities or validation.

Missing evaluation means **untested**, not demonstrated failure. A limitation
of the original paper may have been addressed later; separate historical
contribution from current evidence. Do not replace this analysis with generic
defensive caveats. Compare numbers only under compatible protocols, distinguish
percentage points from relative percentages, and avoid unsupported claims of
statistical significance.

## Content syntax and layout

Use the local toolkit's bilingual layout examples as the syntax reference.
Author `language`, `title`, `meta`, `abstract`, `symbols`, `figures`, and `sections`.
All authored prose must be in the target language. Keep original paper titles,
algorithm names, and source figure text where appropriate.

- Use `$...$` for inline math and
  `{"type":"equation","latex":"y = Wx + b"}` for display equations.
  Escape LaTeX backslashes in JSON. Do not manually number equations.
- A subsection uses `{"type":"heading","level":2,"text":"Core mechanism"}`
  or level 3. Do not type numbering into titles. Chinese numbering is
  一 / 1.1 / 1.1.1; English numbering is 1 / 1.1 / 1.1.1.
- A table uses `type: "table"`, nonempty `headers`, and equal-width `rows`.
  Optional `column_weights` must be positive and match the column count.
  Cells support inline math; place display equations outside tables.
- All native tables are monochrome three-line tables: 1.5 pt top/bottom,
  0.75 pt header separator, no vertical rules, white fill, black text.
  Center the table and every cell horizontally and vertically. Original
  table crops retain their source appearance.
- Top-level figure entries use actual `id`, `path`, `caption`, `width_in`, and
  `height_in`; reference them with `{"type":"figure","fig_id":"actual-id","note":"..."}`.
  Preserve the source ratio; use proportional `max_height_in` / `max_width_in`
  limits when needed. Use paths relative to `content.json` when possible.
- Let the builder apply A4, fonts, sizes, colors, and indentation. Latin text
  uses Times New Roman; Chinese body/headings use SimSun/SimHei. Body and
  headings are black; only math variables use mathematical italics.
- Use `page_break_before` or a `page_break` block at natural boundaries when
  needed. Do not pad pages with empty paragraphs or shrink figures past legibility.
- Include a final source list with usable URLs and precise evidence locations.
  It can be a `References` / `参考文献` section after the five body parts.

## Verification before delivery

Build through the Python CLI with `--verify`. Check the actual returned paths
and exit status. For the exact DOCX being delivered:

1. Confirm the matching PDF has the same stem and was generated after the DOCX.
2. Run `tools/verify_math.py` and clear all issues in its matching
   `.math_audit.json`. Check inline and display math, table cells, captions,
   headings, and notes. Do not mask equations with audit exceptions.
3. Compare source LaTeX, OMML structure, and the rendered placement for every
   subscript/superscript. Inspect fractions, limits, delimiters, and combined
   scripts; zero automated issues does not prove visual correctness.
   Check that `\mathrm` / `\operatorname` labels and `\text` remain upright,
   variables remain italic, and explicit nested font changes keep their scope.
4. Read `verify/layout_audit.json` and inspect **every page**. Confirm front
   matter, numbering, monochrome borders, cell centering, complete figures,
   readable formulas, and sensible pagination. Zoom dense regions.
5. Review nonfinal pages flagged for more than 28% bottom whitespace or 20%
   internal whitespace. These are diagnostics, not orders to fill every page.
   Adjust crops, proportional figure limits, or nearby breaks if helpful.
6. Verify factual claims, baseline classification, concrete abstract results,
   and the external sources/dates for part 5. Scripts do not check scholarship.

For literal code/filename underscores, an exact full-paragraph
`math_review_exceptions` entry with a specific reason is permitted; broad
exemptions and exemptions for residual math markers are not.

After a change, regenerate and recheck the affected output. Deliver only the
files actually inspected and state any unresolved research or rendering gap.
