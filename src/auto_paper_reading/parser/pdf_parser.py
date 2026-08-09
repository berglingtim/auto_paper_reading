"""PDF 解析：抽取文本、标题、摘要，并调用 figures 模块裁剪配图。"""

from __future__ import annotations

import re
from pathlib import Path

import fitz  # pymupdf

from ..models import PaperDocument
from .base import BaseParser

_ABSTRACT_RE = re.compile(r"\babstract\b\s*[:：]?\s*(.*?)(?=\n\s*(?:1\.?\s+)?\b(?:introduction|1\s+intro)\b|\Z)", re.IGNORECASE | re.DOTALL)
_TITLE_LINE_RE = re.compile(r"^\s*(?:\d+\.?[\)\.]?\s*)?(.{10,200})$")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def _guess_title(page0: "fitz.Page") -> str:
    """启发式：首页字号最大的行即标题（多数论文标题字号最大）。"""
    try:
        blocks = page0.get_text("dict")["blocks"]
    except Exception:
        return ""
    lines: list[tuple[str, float]] = []
    for block in blocks:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            text = "".join(s["text"] for s in spans).strip()
            size = max((s.get("size", 0) for s in spans), default=0.0)
            if text and size > 0:
                lines.append((text, size))
    # 过滤非标题行
    filtered = []
    for text, size in lines:
        if _EMAIL_RE.search(text):
            continue
        if re.match(r"^[\s\d\W]+$", text):
            continue
        if re.match(r"^(abstract|doi|https?://|submitted|received|corresponding|keywords?)", text, re.IGNORECASE):
            continue
        if len(text) < 6 or len(text) > 200:
            continue
        filtered.append((text, size))
    if not filtered:
        return ""
    filtered.sort(key=lambda t: t[1], reverse=True)
    best_size = filtered[0][1]
    same_size = [t for t in filtered if t[1] >= best_size * 0.9]
    return max(same_size, key=lambda t: len(t[0]))[0]


def _extract_abstract(text: str, max_len: int = 4000) -> str:
    m = _ABSTRACT_RE.search(text)
    if not m:
        return ""
    ab = re.sub(r"\s+", " ", m.group(1)).strip()
    return ab[:max_len]


def _extract_journal_year(text: str) -> tuple[str, str]:
    """启发式提取期刊/会议名与年份。"""
    journal = ""
    year = ""
    # 常见期刊/会议关键字
    for pat in (
        r"(?:arXiv\s*:?\s*\d{4}\.\d{4,5}(?:v\d+)?)",
        r"(?:Proceedings of the [^\n.]{5,120})",
        r"(?:IEEE (?:Transactions|Journal) on [^\n.]{3,120})",
        r"(?:ACM (?:Transactions|Conference)[^\n.]{0,80})",
        r"(?:Journal of [^\n.]{3,120})",
        r"(?:ICLR|ICML|NeurIPS|CVPR|ICCV|ECCV|ACL|EMNLP|NAACL|AAAI|IJCAI|KDD|SIGGRAPH|MICCAI|WWW)\b[^\n.]{0,60}",
    ):
        m = re.search(pat, text[:6000], re.IGNORECASE)
        if m:
            journal = m.group(0).strip()
            break
    ym = re.search(r"\b(19|20)\d{2}\b", text[:4000])
    if ym:
        year = ym.group(0)
    return journal, year


class PdfParser(BaseParser):
    """基于 pymupdf 的 PDF 解析器。"""

    def parse(self, path: Path, work_dir: Path | None = None) -> PaperDocument:
        path = Path(path)
        doc = fitz.open(path)
        try:
            pages_text = [page.get_text("text") for page in doc]
            text = "\n\n".join(pages_text)

            meta = {k: doc.metadata.get(k) for k in ("title", "author", "subject", "keywords")}
            title = (meta.get("title") or "").strip() or _guess_title(doc[0])
            journal, year = _extract_journal_year(text)

            figures = []
            if work_dir is not None:
                from ..figures import extract_figures

                fig_dir = Path(work_dir) / "figures"
                figures = extract_figures(path, fig_dir)

            return PaperDocument(
                source_path=str(path),
                title=title,
                authors=meta.get("author") or "",
                journal=journal,
                year=year,
                abstract=_extract_abstract(text),
                text=text,
                figures=figures,
                format="pdf",
                metadata={"pages": len(doc), "pdf_meta": meta},
            )
        finally:
            doc.close()
