/**
 * build_docx.js —— 由 content.json 生成图文结合的讲解 docx（基于 docx skill 的 docx-js）。
 *
 * 用法: node tools/build_docx.js <content.json> <out.docx>
 *
 * 格式规范（用户要求）：
 *   - 英语字母和数字：一律 Times New Roman 斜体（中文不受影响）
 *   - 一级标题：黑体 三号(16pt)；二级标题：黑体 四号(14pt)；三级标题：黑体 小四(12pt)
 *   - 正文：宋体 小四(12pt)；专业名词/需标注处用 **加粗**（content.json 文本内用 ** 标记）
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
} = require("docx");

const MAX_W_IN = 6.2; // A4 版心宽度约为 6.27in
const MAX_H_IN = 8.5;

// ---- 字体（Windows 标准字体）----
const CN_BODY = "宋体"; // 正文中文
const CN_HEAD = "黑体"; // 标题中文
const LATIN = "Times New Roman"; // 西文/数字

// ---- 字号（docx-js 单位为半磅）----
const S_BODY = 24; // 小四 12pt
const S_H1 = 32; // 三号 16pt
const S_H2 = 28; // 四号 14pt
const S_H3 = 24; // 小四 12pt
const S_META = 21; // 元信息 10.5pt
const S_TITLE = 36; // 封面标题 18pt

const CJK_RE = /[\u4E00-\u9FFF\u3000-\u303F\uFF00-\uFFEF]/; // 汉字 + 中文标点 + 全角字符
const LATIN_RE = /[A-Za-z0-9]/;

/**
 * 把文本按字符类别切成 [kind, text] 段：
 *   "cjk"   —— 中文/中文标点（用中文正体字体，不斜体）
 *   "latin" —— 英文字母与数字（Times New Roman 斜体）
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
 * - 中文用 cnFont（正体），英文/数字用 Times New Roman 斜体
 */
const MATH_MARK_S = "\uE000";
const MATH_MARK_E = "\uE001";

function makeRuns(text, cnFont, size, allBold = false) {
  const runs = [];
  const parts = String(text).split(/\$([^$]*)\$/); // 奇数下标为公式
  parts.forEach((part, idx) => {
    if (!part) return;
    if (idx % 2 === 1) {
      runs.push(new TextRun({ text: MATH_MARK_S + part + MATH_MARK_E }));
      return;
    }
    const subs = part.split("**");
    subs.forEach((seg, j) => {
      if (!seg) return;
      const bold = j % 2 === 1 || allBold;
      for (const [kind, chunk] of segmentText(seg)) {
        const opts = { size, font: { ascii: LATIN, eastAsia: cnFont, hAnsi: LATIN } };
        if (kind === "latin") opts.italics = true; // 英文/数字一律斜体
        if (bold) opts.bold = true;
        runs.push(new TextRun({ text: chunk, ...opts }));
      }
    });
  });
  return runs;
}

function bodyParagraph(line, opts = {}) {
  return new Paragraph({
    spacing: { after: opts.after != null ? opts.after : 120 },
    alignment: opts.alignment || AlignmentType.LEFT,
    children: makeRuns(line, CN_BODY, opts.size || S_BODY),
  });
}

function headingParagraph(text, level) {
  const map = {
    1: { size: S_H1, heading: HeadingLevel.HEADING_1 },
    2: { size: S_H2, heading: HeadingLevel.HEADING_2 },
    3: { size: S_H3, heading: HeadingLevel.HEADING_3 },
  };
  const cfg = map[level] || map[1];
  return new Paragraph({
    heading: cfg.heading,
    spacing: { before: 360, after: 200 },
    children: makeRuns(text, CN_HEAD, cfg.size),
  });
}

function fitSize(widthIn, heightIn) {
  let w = Math.max(0.5, Number(widthIn) || 6.0);
  let h = Math.max(0.5, Number(heightIn) || 4.0);
  const k = Math.min(MAX_W_IN / w, MAX_H_IN / h, 1);
  return { width: Math.round(w * k * 96), height: Math.round(h * k * 96) };
}

function figureParagraph(fig, contentPath) {
  const imgPath = resolvePath(contentPath, fig && fig.path);
  if (!imgPath || !fs.existsSync(imgPath)) {
    return bodyParagraph(`[图片缺失: ${fig ? fig.id : "unknown"}]`, { size: S_META });
  }
  const ext = path.extname(imgPath).toLowerCase().replace(".", "") || "png";
  const size = fitSize(fig.width_in, fig.height_in);
  return new Paragraph({
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
    paras.push(
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 60 },
        children: makeRuns(`图注：${fig.caption}`, CN_BODY, S_META),
      })
    );
  }
  if (note) {
    for (const line of String(note).split("\n")) {
      paras.push(
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 240 },
          children: makeRuns(line, CN_BODY, S_META),
        })
      );
    }
  }
  return paras;
}

function build(content, contentPath) {
  const children = [];
  const figures = content.figures || [];

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
  const metaParts = [meta.journal, meta.year ? `${meta.year} 年` : "", meta.authors].filter(Boolean);
  if (metaParts.length) {
    children.push(
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 400 },
        children: makeRuns(metaParts.join(" · "), CN_BODY, S_META),
      })
    );
  }

  // ---- 正文 ----
  for (const sec of content.sections || []) {
    if (sec.title) {
      children.push(headingParagraph(sec.title, 1));
    }
    for (const block of sec.blocks || []) {
      if (block.type === "heading") {
        const level = Number(block.level) || 2;
        if (level >= 2 && level <= 3) {
          children.push(headingParagraph(block.text || "", level));
        }
        continue;
      }
      if (block.type === "figure") {
        const fig = figures.find((f) => f.id === block.fig_id) || null;
        children.push(figureParagraph(fig, contentPath));
        for (const p of captionParagraph(fig, block.note)) children.push(p);
      } else {
        const text = String(block.text || "");
        for (const line of text.split("\n")) {
          children.push(bodyParagraph(line));
        }
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
          },
        },
      },
    },
    sections: [{ children }],
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
