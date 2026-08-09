""".doc / .docx 解析：先经 WPS 转为 PDF，再复用 PDF 解析器（统一管线）。"""

from __future__ import annotations

from pathlib import Path

from ..models import PaperDocument
from .base import BaseParser
from .convert import doc_to_pdf
from .pdf_parser import PdfParser


class DocxParser(BaseParser):
    """Word 文档解析器：转 PDF 后走同一套 PDF 解析逻辑。

    好处：图文版面信息（图片位置、图注）与 PDF 完全一致；
    代价：依赖本机 WPS Office 完成转换。
    """

    def parse(self, path: Path, work_dir: Path | None = None) -> PaperDocument:
        path = Path(path)
        if path.suffix.lower() not in (".doc", ".docx"):
            raise ValueError(f"不支持的 Word 格式: {path.suffix}")

        work_dir = Path(work_dir) if work_dir else path.parent / f"{path.stem}_work"
        work_dir.mkdir(parents=True, exist_ok=True)

        pdf_path = doc_to_pdf(path, work_dir)
        paper = PdfParser().parse(pdf_path, work_dir)
        paper.source_path = str(path)
        paper.format = path.suffix.lower().lstrip(".")
        paper.metadata["converted_pdf"] = str(pdf_path)
        return paper
