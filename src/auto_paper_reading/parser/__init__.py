"""解析调度入口：按扩展名路由到对应解析器。"""

from __future__ import annotations

from pathlib import Path

from ..models import PaperDocument
from .base import BaseParser
from .docx_parser import DocxParser
from .pdf_parser import PdfParser

SUPPORTED_EXTENSIONS = (".pdf", ".docx", ".doc")


def parse_paper(path: str | Path, work_dir: str | Path | None = None) -> PaperDocument:
    """解析任意支持的论文格式，统一返回 PaperDocument。

    Args:
        path: 论文路径（.pdf / .docx / .doc）。
        work_dir: 工作目录，用于存放裁剪图片等中间产物；为 None 则不裁剪图片。

    Raises:
        FileNotFoundError: 文件不存在。
        ValueError: 不支持的格式。
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"论文文件不存在: {p}")
    ext = p.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"不支持的格式 {ext!r}，仅支持: {', '.join(SUPPORTED_EXTENSIONS)}")

    parser: BaseParser = PdfParser() if ext == ".pdf" else DocxParser()
    return parser.parse(p, Path(work_dir) if work_dir else None)


__all__ = ["parse_paper", "SUPPORTED_EXTENSIONS", "BaseParser", "PdfParser", "DocxParser"]
