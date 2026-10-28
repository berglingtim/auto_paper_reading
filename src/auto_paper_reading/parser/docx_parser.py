""".doc / .docx 解析：默认经 LibreOffice 转为 PDF，再复用 PDF 解析器。"""

from __future__ import annotations

from pathlib import Path

from ..models import PaperDocument
from .base import BaseParser
from .convert import doc_to_pdf
from .pdf_parser import PdfParser


class DocxParser(BaseParser):
    """Word 文档解析器：转 PDF 后走同一套 PDF 解析逻辑。

    好处：图文版面信息（图片位置、图注）与 PDF 完全一致；
    默认使用免费的 LibreOffice；WPS 仅作显式选择的兼容后端。
    """

    def __init__(self, backend: str = "libreoffice"):
        self.backend = backend

    def parse(self, path: Path, work_dir: Path | None = None) -> PaperDocument:
        path = Path(path)
        if path.suffix.lower() not in (".doc", ".docx"):
            raise ValueError(f"不支持的 Word 格式: {path.suffix}")

        work_dir = Path(work_dir) if work_dir else path.parent / f"{path.stem}_work"
        work_dir.mkdir(parents=True, exist_ok=True)

        pdf_path = doc_to_pdf(path, work_dir, backend=self.backend)
        paper = PdfParser().parse(pdf_path, work_dir)
        paper.source_path = str(path)
        paper.format = path.suffix.lower().lstrip(".")
        paper.metadata["converted_pdf"] = str(pdf_path)
        paper.metadata["pdf_backend"] = self.backend
        return paper
