/**
 * build_docx.js —— 由 content.json 生成图文结合的讲解 docx（基于 docx skill 的 docx-js）。
 *
 * 用法: node tools/build_docx.js <content.json> <out.docx>
 *
 * content.json 结构见 src/auto_paper_reading/docx_content.py 的注释。
 * 图片宽度/高度由 Python 侧按英寸给出，这里按 96dpi 换算像素并限制在版心内。
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
const CN_FONT = "微软雅黑";
const BODY_SIZE = 22; // 11pt
const NOTE_SIZE = 18; // 9pt

function fitSize(widthIn, heightIn) {
  let w = Math.max(0.5, Number(widthIn) || 6.0);
  let h = Math.max(0.5, Number(heightIn) || 4.0);
  const k = Math.min(MAX_W_IN / w, MAX_H_IN / h, 1);
  return { width: Math.round(w * k * 96), height: Math.round(h * k * 96) };
}

function resolvePath(contentPath, p) {
  if (!p) return p;
  if (path.isAbsolute(p)) return p;
  return path.resolve(path.dirname(contentPath), p);
}

function figureParagraph(fig, contentPath) {
  const imgPath = resolvePath(contentPath, fig && fig.path);
  if (!imgPath || !fs.existsSync(imgPath)) {
    return new Paragraph({
      children: [
        new TextRun({
          text: `[图片缺失: ${fig ? fig.id : "unknown"}]`,
          italics: true,
          color: "999999",
          size: NOTE_SIZE,
          font: CN_FONT,
        }),
      ],
    });
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

function captionParagraph(fig, note) {
  const children = [];
  if (fig && fig.caption) {
    children.push(
      new TextRun({ text: `图注：${fig.caption}`, italics: true, size: NOTE_SIZE, color: "666666", font: CN_FONT })
    );
  }
  if (note) {
    const lines = String(note).split("\n");
    lines.forEach((line, i) => {
      if (children.length > 0 && i > 0) {
        // 多行说明时另起段落
      }
      children.push(
        new TextRun({
          text: line + (i < lines.length - 1 ? "\n" : ""),
          size: NOTE_SIZE,
          color: "444444",
          font: CN_FONT,
        })
      );
    });
  }
  return children.length
    ? new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 240 },
        children,
      })
    : null;
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
        children: [new TextRun({ text: title, bold: true, size: 36, font: CN_FONT })],
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
        children: [new TextRun({ text: metaParts.join(" · "), size: 20, color: "555555", font: CN_FONT })],
      })
    );
  }

  // ---- 正文 ----
  for (const sec of content.sections || []) {
    if (sec.title) {
      children.push(
        new Paragraph({
          heading: HeadingLevel.HEADING_1,
          spacing: { before: 360, after: 200 },
          children: [new TextRun({ text: sec.title, bold: true, size: 30, font: CN_FONT })],
        })
      );
    }
    for (const block of sec.blocks || []) {
      if (block.type === "figure") {
        const fig = figures.find((f) => f.id === block.fig_id) || null;
        children.push(figureParagraph(fig, contentPath));
        const cap = captionParagraph(fig, block.note);
        if (cap) children.push(cap);
      } else {
        const text = String(block.text || "");
        for (const line of text.split("\n")) {
          children.push(
            new Paragraph({
              spacing: { after: 120 },
              children: [new TextRun({ text: line, size: BODY_SIZE, font: CN_FONT })],
            })
          );
        }
      }
    }
  }

  return new Document({
    styles: {
      default: {
        document: {
          run: { font: { ascii: "Calibri", eastAsia: CN_FONT, hAnsi: "Calibri" }, size: BODY_SIZE },
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
