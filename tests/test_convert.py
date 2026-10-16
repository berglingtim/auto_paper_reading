"""WPS 转换测试（.docx → PDF）。WPS 不可用时自动跳过。"""


import pytest

from auto_paper_reading.parser import parse_paper  # noqa: E402
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


def test_docx_requires_allow_wps(tmp_path):
    """未显式允许 WPS 时，.docx 输入必须直接报错（不触发任何 WPS 调用）。"""
    import docx as pydocx

    src = tmp_path / "t.docx"
    d = pydocx.Document()
    d.add_paragraph("hello")
    d.save(src)

    with pytest.raises(RuntimeError, match="allow-wps"):
        parse_paper(src, work_dir=tmp_path / "work")
