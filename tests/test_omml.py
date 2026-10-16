"""omml.py（LaTeX→OMML）单元测试。"""


from lxml import etree

from auto_paper_reading.omml import LatexError, latex_to_omml  # noqa: E402

M = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"


def _tags(latex: str) -> list[str]:
    el = latex_to_omml(latex)
    return sorted({etree.QName(c).localname for c in el.iter()})


def test_superscript():
    assert "sSup" in _tags(r"x^2")


def test_subscript_superscript_combined():
    tags = _tags(r"P_i^{(j)}")
    assert "sSubSup" in tags  # i 为下标、(j) 为上标 → 组合


def test_fraction():
    tags = _tags(r"\frac{1}{m}")
    assert "f" in tags and "num" in tags and "den" in tags


def test_sum_with_limits():
    tags = _tags(r"\sum_{k=1}^{m}\sigma(z_k)")
    assert "nary" in tags
    xml = etree.tostring(latex_to_omml(r"\sum_{k=1}^{m} x"), encoding="unicode")
    assert "∑" in xml


def test_mathbb_bold():
    el = latex_to_omml(r"\mathbb{R}^{256\times 1024}")
    xml = etree.tostring(el, encoding="unicode")
    assert "×" in xml
    assert "sty" in xml  # 粗体样式
    assert "sSup" in {etree.QName(c).localname for c in el.iter()}


def test_delimiter_left_right():
    tags = _tags(r"2\left|\sigma(z_i)-0.5\right|")
    assert "d" in tags and "dPr" in tags
    xml = etree.tostring(latex_to_omml(r"\left(x+1\right)")).decode()
    assert 'begChr' in xml and 'endChr' in xml


def test_function_log():
    el = latex_to_omml(r"L_{avg}=-(p\log p+(1-p)\log(1-p))")
    tags = {etree.QName(c).localname for c in el.iter()}
    assert "func" in tags and "sSub" in tags


def test_accent_hat():
    assert "acc" in _tags(r"\hat{D}")


def test_sqrt():
    assert "rad" in _tags(r"\sqrt{x}")


def test_empty_raises():
    try:
        latex_to_omml("")
    except LatexError:
        pass
    else:
        raise AssertionError("空公式应报 LatexError")
