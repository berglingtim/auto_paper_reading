"""PDF 解析与配图裁剪测试：构造含光栅图 + 矢量图 + 图注的样例 PDF。"""

from pathlib import Path

import fitz  # pymupdf
import pytest

from auto_paper_reading.parser import parse_paper  # noqa: E402


@pytest.fixture(scope="module")
def sample_pdf(tmp_path_factory):
    """生成一页两图 + 标题摘要的样例论文 PDF。"""
    out = tmp_path_factory.mktemp("pdf") / "sample.pdf"
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4

    # 标题/作者/摘要
    page.insert_text((72, 72), "Attention Is All You Need Revisited", fontsize=16)
    page.insert_text((72, 92), "Test Author", fontsize=10)
    page.insert_text((72, 112), "Abstract: A novel method for sequence modeling.", fontsize=9)

    # 光栅图：画一个矩形区域并嵌入一张小图（模拟 Figure 1）
    img = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 120, 80), False)
    img.clear_with(200)  # 灰色底
    xref = doc._getXrefImage(img) if hasattr(doc, "_getXrefImage") else None
    rect1 = fitz.Rect(72, 140, 400, 280)
    page.insert_image(rect1, pixmap=img)
    page.insert_text((72, 300), "Figure 1: The overall architecture of our method.", fontsize=9)

    # 矢量图：仅画线条/方块，不嵌入图片（模拟 Figure 2，靠图注定位）
    r = fitz.Rect(72, 380, 400, 520)
    page.draw_rect(fitz.Rect(90, 400, 250, 460), color=(0, 0, 1), width=1.5)
    page.draw_line(fitz.Point(170, 460), fitz.Point(170, 500), color=(1, 0, 0), width=1.5)
    page.draw_rect(fitz.Rect(120, 500, 220, 540), color=(0, 0.6, 0), width=1.5)
    page.insert_text((72, 560), "Figure 2: Detailed view of the attention module.", fontsize=9)

    # 正文
    page.insert_text((72, 600), "1 Introduction", fontsize=11)
    page.insert_text((72, 615), "As shown in Figure 1 and Figure 2, our method works well.", fontsize=9)

    doc.save(out)
    doc.close()
    return out


def test_parse_pdf_extracts_figures(sample_pdf):
    work = sample_pdf.parent / "work"
    paper = parse_paper(sample_pdf, work_dir=work)

    assert paper.title
    assert "Abstract" in paper.abstract or paper.abstract
    assert len(paper.figures) >= 2, f"期望至少 2 张图，实际 {len(paper.figures)}"

    # 图注应被正确关联
    captions = [f.caption for f in paper.figures]
    assert any("Figure 1" in c for c in captions)
    assert any("Figure 2" in c for c in captions)

    # 裁剪文件存在
    for f in paper.figures:
        assert Path(f.image_path).exists(), f"裁剪文件缺失: {f.image_path}"


def test_unsupported_format(tmp_path):
    bad = tmp_path / "x.txt"
    bad.write_text("hi", encoding="utf-8")
    with pytest.raises(ValueError):
        parse_paper(bad)


def test_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        parse_paper(tmp_path / "nope.pdf")
