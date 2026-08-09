"""WPS 转换测试（.docx → PDF）。WPS 不可用时自动跳过。"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from auto_paper_reading.parser.convert import doc_to_pdf, find_wps_convert  # noqa: E402


@pytest.mark.skipif(find_wps_convert() is None, reason="未找到 WPS kwpsconvert.exe")
def test_docx_to_pdf(tmp_path):
    import docx as pydocx

    src = tmp_path / "t.docx"
    d = pydocx.Document()
    d.add_heading("测试", 0)
    d.add_paragraph("hello")
    d.save(src)

    pdf = doc_to_pdf(src, tmp_path / "out")
    assert pdf.exists()
    assert pdf.suffix == ".pdf"
