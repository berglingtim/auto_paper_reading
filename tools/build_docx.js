/**
 * build_docx.js —— 由 content.json 生成图文结合的讲解 docx（基于 docx skill 的 docx-js）。
 *
 * 用法: node tools/build_docx.js <content.json> <out.docx>
 *
 * 格式规范（用户要求）：
 *   - 英语字母和数字：一律 Times New Roman 正体（中文不受影响；仅公式变量斜体，
 *     斜体由 OMML 数学样式承担，其他情况不做改变）
 *   - 一级标题：黑体 三号(16pt)；二级标题：黑体 四号(14pt)；三级标题：黑体 小四(12pt)
 *   - 正文：宋体 小四(12pt)；专业名词/需标注处用 **加粗**（content.json 文本内用 ** 标记）
 *   - 表格中的文字：小五(9pt)；参考文献：六号(7.5pt，整节匹配"参考文献/References"生效)
 *
 * content.json 结构见 src/auto_paper_reading/docx_content.py 的注释，另支持：
 *   - blocks 中 {"type":"heading","level":2|3,"text":"..."} 输出二级/三级标题
 *   - 任意文本字段中 `**术语**` 表示加粗
 */
"use strict";

const fs = require("fs");
const path = require("path");
const {
  Document,
  Packer,
  Paragraph,
  TextRun,
  ImageRun,
  HeadingLevel,
  AlignmentType,
  TabStopType,
  Table,
  TableRow,
  TableCell,
  WidthType,
  TableLayoutType,
  BorderStyle,
  ShadingType,
  VerticalAlign,
} = require("docx");

const MAX_W_IN = 6.2; // A4 版心宽度约为 6.27in
const MAX_H_IN = 8.0; // 为图注保留至少约 1.7in 的版心空间
const DEFAULT_FIGURE_HEIGHT = 4.5;
const PAGE_WIDTH = 11906;
const PAGE_MARGIN = 1440;
const TEXT_WIDTH = PAGE_WIDTH - 2 * PAGE_MARGIN;
let equationCounter = 0;
let pageBreakPending = false;
let reportLayout = {};
let reportLanguage = "zh";
const LABELS = {
  zh: {
    abstract: "摘要", notation: "符号表", unspecified: "原文未说明",
    emptyNotation: "本篇无需单独列示核心符号，简单变量在正文随用随释。",
    headers: ["符号", "中文含义", "类型／维度", "作用", "出处／适用范围"],
    caption: "图注：", missingImage: "图片缺失",
  },
  en: {
    abstract: "Abstract", notation: "Notation", unspecified: "Not specified in the paper",
    emptyNotation: "No separate notation table is needed; simple variables are explained where they appear.",
    headers: ["Symbol", "Meaning", "Type / shape", "Role", "Source / scope"],
    caption: "Caption: ", missingImage: "Missing image",
  },
};
let labels = LABELS.zh;

function pageStartOptions() {
  const pageBreakBefore = pageBreakPending;
  pageBreakPending = false;
  return { pageBreakBefore };
}

// ---- 字体（Windows 标准字体）----
const CN_BODY = "宋体"; // 正文中文
const CN_HEAD = "黑体"; // 标题中文
const LATIN = "Times New Roman"; // 西文/数字

// ---- 字号（docx-js 单位为半磅）----
const S_BODY = 24; // 小四 12pt
const S_H1 = 32; // 三号 16pt
const S_H2 = 28; // 四号 14pt
const S_H3 = 24; // 小四 12pt
const S_META = 21; // 元信息/图注 10.5pt
const S_TITLE = 36; // 封面标题 18pt
const S_TABLE = 18; // 表格中的文字 小五 9pt
const S_REFS = 15; // 参考文献 六号 7.5pt

const CJK_RE = /[\u4E00-\u9FFF\u3000-\u303F\uFF00-\uFFEF]/; // 汉字 + 中文标点 + 全角字符
const LATIN_RE = /[A-Za-z0-9]/;

/**
 * 把文本按字符类别切成 [kind, text] 段：
 *   "cjk"   —— 中文/中文标点（用中文正体字体，不斜体）
 *   "latin" —— 英文字母与数字（Times New Roman 正体）
 *   "other" —— 空格、ASCII 标点、数学符号等（Times New Roman 正体）
 */
function segmentText(text) {
  const segs = [];
  let cur = "";
  let kind = null;
  for (const ch of text) {
    let k;
    if (CJK_RE.test(ch)) k = "cjk";
    else if (LATIN_RE.test(ch)) k = "latin";
    else k = "other";
    if (k !== kind && cur) {
      segs.push([kind, cur]);
      cur = "";
    }
    kind = k;
    cur += ch;
  }
  if (cur) segs.push([kind, cur]);
  return segs;
}

/**
 * 生成一行文本的 TextRun 数组。
 * - `$...$` 数学公式 → 私有区字符包裹的占位 run（后续由 Python 注入 OMML，WPS 原生渲染）
 * - `**...**` 标记加粗（奇数段加粗）
 * - 中文用 cnFont（正体），英文/数字用 Times New Roman 正体（仅公式变量斜体）
 */
const MATH_MARK_S = "\uE000";
const MATH_MARK_E = "\uE001";

function makeRuns(text, cnFont, size, allBold = false) {
  const runs = [];
  const parts = String(text).split(/\$([^$]*)\$/); // 奇数下标为公式
  parts.forEach((part, idx) => {
    if (!part) return;
    if (idx % 2 === 1) {
      runs.push(new TextRun({ text: MATH_MARK_S + part + MATH_MARK_E, size }));
      return;
    }
    const subs = part.split("**");
    subs.forEach((seg, j) => {
      if (!seg) return;
      const bold = j % 2 === 1 || allBold;
      for (const [kind, chunk] of segmentText(seg)) {
        const opts = {
          size,
          color: "000000", // 全文档统一黑色（覆盖标题样式自带的主题蓝）
          font: { ascii: LATIN, eastAsia: cnFont, hAnsi: LATIN },
        };
        // 西文/数字一律 Times New Roman 正体（仅公式变量斜体，由 OMML 数学样式承担）
        if (bold) opts.bold = true;
        runs.push(new TextRun({ text: chunk, ...opts }));
      }
    });
  });
  return runs;
}

function bodyParagraph(line, opts = {}) {
  const size = opts.size || S_BODY;
  const alignment = opts.alignment || AlignmentType.JUSTIFIED;
  return new Paragraph({
    ...pageStartOptions(),
    keepLines: Boolean(opts.keepLines),
    keepNext: Boolean(opts.keepNext),
    spacing: { after: opts.after != null ? opts.after : 120 },
    alignment,
    // 字号为半磅；两个汉字宽度 = size 磅 = size * 20 twips。
    indent: { firstLine: alignment === AlignmentType.JUSTIFIED ? size * 20 : 0 },
    children: makeRuns(line, CN_BODY, size),
  });
}

function equationParagraph(latex) {
  if (!String(latex).trim()) throw new Error("公式内容不能为空");
  equationCounter += 1;
  return new Paragraph({
    ...pageStartOptions(),
    spacing: { before: 120, after: 120 },
    keepLines: true,
    tabStops: [
      { type: TabStopType.CENTER, position: TEXT_WIDTH / 2 },
      { type: TabStopType.RIGHT, position: TEXT_WIDTH },
    ],
    children: [
      new TextRun({ text: "\t" }),
      new TextRun({ text: MATH_MARK_S + String(latex).trim() + MATH_MARK_E }),
      ...makeRuns(reportLanguage === "en" ? `\t(${equationCounter})` : `\t（${equationCounter}）`, CN_BODY, S_BODY),
    ],
  });
}

// 仅 $$...$$ 拆为编号公式；$...$ 留在段内由 makeRuns 注入数学对象。
function textParagraphs(text, opts = {}) {
  const parts = String(text).split(/\$\$([\s\S]*?)\$\$/g);
  const paras = [];
  for (let i = 0; i < parts.length; i += 2) {
    for (const line of parts[i].split(/\r?\n/)) {
      if (line.trim()) paras.push(bodyParagraph(line, opts));
    }
    const latex = parts[i + 1];
    if (latex !== undefined) paras.push(equationParagraph(latex));
  }
  return paras;
}

// 三级标题自动编号状态（一 / 1.1 / 1.1.1），内部章节计数仍用整数。
let headingCounters = [0, 0, 0];

function chineseChapterNumber(n, leading = true) {
  if (n < 10) return "零一二三四五六七八九"[n];
  const [base, unit] = [[100000000, "亿"], [10000, "万"], [1000, "千"],
    [100, "百"], [10, "十"]].find(([value]) => n >= value);
  const prefix = leading && base === 10 && n < 20 ? "" : chineseChapterNumber(Math.floor(n / base));
  const rest = n % base;
  return prefix + unit + (rest ? (rest < base / 10 ? "零" : "") + chineseChapterNumber(rest, false) : "");
}

function headingParagraph(text, level, numbered = true) {
  const map = {
    1: { size: S_H1, heading: HeadingLevel.HEADING_1 },
    2: { size: S_H2, heading: HeadingLevel.HEADING_2 },
    3: { size: S_H3, heading: HeadingLevel.HEADING_3 },
  };
  const cfg = map[level] || map[1];
  // 自动编号
  if (numbered && level === 1) {
    headingCounters[0] += 1;
    headingCounters[1] = 0;
    headingCounters[2] = 0;
  } else if (numbered && level === 2) {
    headingCounters[1] += 1;
    headingCounters[2] = 0;
  } else if (numbered && level === 3) {
    headingCounters[2] += 1;
  }
  let num;
  if (level === 1) num = reportLanguage === "en" ? String(headingCounters[0]) : chineseChapterNumber(headingCounters[0]);
  else if (level === 2) num = `${headingCounters[0]}.${headingCounters[1]}`;
  else num = `${headingCounters[0]}.${headingCounters[1]}.${headingCounters[2]}`;
  const fullText = numbered ? `${num} ${text}` : text;
  return new Paragraph({
    ...pageStartOptions(),
    keepNext: true,
    keepLines: true,
    heading: cfg.heading,
    spacing: { before: 360, after: 200 },
    children: makeRuns(fullText, CN_HEAD, cfg.size),
  });
}

/** 黑白三线表；单元格水平/垂直居中，表头跨页重复。边框 size 单位为 1/8 pt。 */
function contentTable(block) {
  const { headers, rows } = block;
  if (!Array.isArray(headers) || !headers.length ||
      !headers.every(h => typeof h === "string" && h.trim()) ||
      !Array.isArray(rows) || rows.some(r => !Array.isArray(r) || r.length !== headers.length)) {
    throw new Error("表格必须有非空 headers，且 rows 每行列数与表头一致");
  }
  const weights = block.column_weights ?? headers.map(() => 1);
  if (!Array.isArray(weights) || weights.length !== headers.length ||
      !weights.every(w => typeof w === "number" && Number.isFinite(w) && w > 0)) {
    throw new Error("column_weights 必须为与表头等长的正数数组");
  }
  const sum = weights.reduce((a, b) => a + b, 0);
  const widths = weights.map(w => Math.floor(TEXT_WIDTH * w / sum));
  widths[widths.length - 1] += TEXT_WIDTH - widths.reduce((a, b) => a + b, 0);
  const outerLine = { style: BorderStyle.SINGLE, size: 12, color: "000000" };
  const headerLine = { style: BorderStyle.SINGLE, size: 6, color: "000000" };
  const noLine = { style: BorderStyle.NIL };
  return new Table({
    alignment: AlignmentType.CENTER,
    width: { size: TEXT_WIDTH, type: WidthType.DXA },
    columnWidths: widths,
    layout: TableLayoutType.FIXED,
    borders: { top: outerLine, bottom: outerLine, left: noLine, right: noLine,
      insideHorizontal: noLine, insideVertical: noLine },
    rows: [headers, ...rows].map((row, rowIndex) => new TableRow({
      tableHeader: rowIndex === 0,
      cantSplit: true,
      children: row.map((value, columnIndex) => {
        if (typeof value !== "string" && typeof value !== "number") {
          throw new Error("表格单元格必须为文字或数字");
        }
        const text = String(value);
        if (text.includes("$$")) throw new Error("表格内请用 $...$ 行内公式，独立公式放在表格外");
        return new TableCell({
          width: { size: widths[columnIndex], type: WidthType.DXA },
          verticalAlign: VerticalAlign.CENTER,
          margins: { top: 100, bottom: 100, left: 100, right: 100 },
          shading: { type: ShadingType.CLEAR, fill: "FFFFFF" },
          borders: rowIndex === 0 ? { bottom: headerLine } : undefined,
          children: text.split(/\r?\n/).map(line => new Paragraph({
            // 分页标记只由第一格的第一段消耗；单元格不使用正文首行缩进。
            ...pageStartOptions(),
            alignment: AlignmentType.CENTER,
            spacing: { before: 0, after: 0 },
            children: makeRuns(line, CN_BODY, S_TABLE, rowIndex === 0),
          })),
        });
      }),
    })),
  });
}

function frontMatter(content) {
  const children = [];
  if (content.abstract !== undefined) {
    if (typeof content.abstract !== "string" || !content.abstract.trim()) {
      throw new Error("abstract 必须为非空摘要文字 / must be a non-empty summary in the report language");
    }
    children.push(headingParagraph(labels.abstract, 1, false), ...textParagraphs(content.abstract));
  }
  if (content.symbols !== undefined) {
    if (!Array.isArray(content.symbols)) throw new Error("symbols 必须为数组");
    children.push(headingParagraph(labels.notation, 1, false));
    if (!content.symbols.length) {
      children.push(bodyParagraph(labels.emptyNotation));
    } else {
      const rows = content.symbols.map(s => {
        if (!s || typeof s.symbol !== "string" || !s.symbol.trim() ||
            typeof s.meaning !== "string" || !s.meaning.trim()) {
          throw new Error("每个符号必须有非空的 symbol 和 meaning");
        }
        return [s.symbol, s.meaning, s.shape ?? labels.unspecified, s.role ?? "", s.source ?? ""];
      });
      children.push(contentTable({
        headers: labels.headers,
        rows, column_weights: [1, 1.8, 1.8, 2.4, 1.8],
      }));
    }
  }
  return children;
}

function fitSize(widthIn, heightIn, maxHeightIn, maxWidthIn) {
  let w = Math.max(0.5, Number(widthIn) || 6.0);
  let h = Math.max(0.5, Number(heightIn) || 4.0);
  const maxH = Math.min(MAX_H_IN, positiveSize(maxHeightIn, DEFAULT_FIGURE_HEIGHT));
  const maxW = Math.min(MAX_W_IN, positiveSize(maxWidthIn, MAX_W_IN));
  const k = Math.min(maxW / w, maxH / h, 1);
  return { width: Math.round(w * k * 96), height: Math.round(h * k * 96) };
}

function positiveSize(value, fallback) {
  if (value == null) return fallback;
  const n = Number(value);
  if (!Number.isFinite(n) || n <= 0) throw new Error("图片尺寸上限必须是正数");
  return n;
}

function figureParagraph(fig, contentPath, block = {}) {
  const imgPath = resolvePath(contentPath, fig && fig.path);
  if (!imgPath || !fs.existsSync(imgPath)) {
    return bodyParagraph(`[${labels.missingImage}: ${fig ? fig.id : "unknown"}]`, { size: S_META });
  }
  const ext = path.extname(imgPath).toLowerCase().replace(".", "") || "png";
  const size = fitSize(fig.width_in, fig.height_in,
    block.max_height_in ?? fig.max_height_in ?? reportLayout.max_figure_height_in,
    block.max_width_in ?? fig.max_width_in ?? reportLayout.max_figure_width_in);
  return new Paragraph({
    ...pageStartOptions(),
    keepNext: Boolean(fig.caption),
    keepLines: true,
    alignment: AlignmentType.CENTER,
    spacing: { before: 120, after: 60 },
    children: [
      new ImageRun({
        type: ext,
        data: fs.readFileSync(imgPath),
        transformation: size,
      }),
    ],
  });
}

function resolvePath(contentPath, p) {
  if (!p) return p;
  if (path.isAbsolute(p)) return p;
  return path.resolve(path.dirname(contentPath), p);
}

function captionParagraph(fig, note) {
  const paras = [];
  if (fig && fig.caption) {
    paras.push(...textParagraphs(`${labels.caption}${fig.caption}`, {
      alignment: AlignmentType.CENTER, after: 60, size: S_META, keepLines: true,
    }));
  }
  if (note) {
    paras.push(...textParagraphs(note, { after: 240, size: S_META }));
  }
  return paras;
}

function build(content, contentPath) {
  reportLanguage = content.language === undefined ? "zh" : content.language;
  if (!["zh", "en"].includes(reportLanguage)) {
    throw new Error('language 必须是 / must be "zh" or "en"');
  }
  labels = LABELS[reportLanguage];
  const children = [];
  const figures = content.figures || [];
  headingCounters = [0, 0, 0]; // 每次构建重置编号
  equationCounter = 0;
  pageBreakPending = false;
  reportLayout = content.layout || {};

  // ---- 封面信息 ----
  const title = content.title || content.paper_title || "";
  if (title) {
    children.push(
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 120 },
        children: makeRuns(title, CN_HEAD, S_TITLE, true),
      })
    );
  }
  const meta = content.meta || {};
  const metaParts = [meta.journal, meta.year ? `${meta.year}${reportLanguage === "zh" ? " 年" : ""}` : "", meta.authors].filter(Boolean);
  if (metaParts.length) {
    children.push(
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 400 },
        children: makeRuns(metaParts.join(" · "), CN_BODY, S_META),
      })
    );
  }

  // ---- 摘要与符号表始终在正文之前，不占用正文标题编号 ----
  children.push(...frontMatter(content));

  // ---- 正文 ----
  for (const sec of content.sections || []) {
    if (sec.page_break_before) pageBreakPending = true;
    if (sec.title) {
      children.push(headingParagraph(sec.title, 1));
    }
    const isRefs = /参考文献|references/i.test(sec.title || ""); // 参考文献整节六号
    for (const block of sec.blocks || []) {
      if (block.type === "page_break") {
        pageBreakPending = true;
        continue;
      }
      if (block.page_break_before) pageBreakPending = true;
      if (block.type === "heading") {
        const level = Number(block.level) || 2;
        if (level >= 2 && level <= 3) {
          children.push(headingParagraph(block.text || "", level));
        }
        continue;
      }
      if (block.type === "equation") {
        children.push(equationParagraph(block.latex || block.text || ""));
      } else if (block.type === "table") {
        children.push(contentTable(block));
      } else if (block.type === "figure") {
        const fig = figures.find((f) => f.id === block.fig_id) || null;
        children.push(figureParagraph(fig, contentPath, block));
        for (const p of captionParagraph(fig, block.note)) children.push(p);
      } else {
        const text = String(block.text || "");
        children.push(...textParagraphs(text, isRefs ? { size: S_REFS } : {}));
      }
    }
  }

  return new Document({
    styles: {
      default: {
        document: {
          run: {
            color: "000000", // 字体统一黑色（含公式继承）
            font: { ascii: LATIN, eastAsia: CN_BODY, hAnsi: LATIN },
            size: S_BODY,
            language: { value: reportLanguage === "en" ? "en-US" : "zh-CN" },
          },
        },
      },
      // 显式覆盖内置标题样式：去掉主题蓝，统一黑色（黑体由 run 层保证）
      paragraphStyles: [
        { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { color: "000000" } },
        { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { color: "000000" } },
        { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true, run: { color: "000000" } },
        { id: "Title", name: "Title", basedOn: "Normal", next: "Normal", quickFormat: true, run: { color: "000000" } },
      ],
    },
    sections: [{
      properties: { page: {
        size: { width: PAGE_WIDTH, height: 16838 },
        margin: { top: PAGE_MARGIN, bottom: PAGE_MARGIN, left: PAGE_MARGIN, right: PAGE_MARGIN },
      } },
      children,
    }],
  });
}

async function main() {
  const [, , contentPath, outPath] = process.argv;
  if (!contentPath || !outPath) {
    console.error("用法: node tools/build_docx.js <content.json> <out.docx>");
    process.exit(1);
  }
  const content = JSON.parse(fs.readFileSync(contentPath, "utf-8"));
  const doc = build(content, contentPath);
  const buf = await Packer.toBuffer(doc);
  fs.mkdirSync(path.dirname(path.resolve(outPath)), { recursive: true });
  fs.writeFileSync(outPath, buf);
  console.log(`OK → ${outPath}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
