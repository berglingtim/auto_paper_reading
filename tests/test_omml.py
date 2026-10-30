"""omml.py（LaTeX→OMML）单元测试。"""


from lxml import etree
import pytest

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


@pytest.mark.parametrize("command,label,style", [
    ("mathrm", "Attention", "p"),
    ("operatorname", "softmax", "p"),
    ("mathit", "uv", "i"),
])
def test_explicit_math_font_is_preserved_without_changing_following_variable(command, label, style):
    """Dropping a font command must not silently turn a label into italic variables."""
    root = latex_to_omml("\\" + command + "{" + label + "}+x")
    runs = list(root.iter(M + "r"))
    label_runs = runs[:-2]
    assert "".join(r.find(M + "t").text for r in label_runs) == label
    assert all(r.find(M + "rPr/" + M + "sty") is not None for r in label_runs)
    assert [r.find(M + "rPr/" + M + "sty").get(M + "val") for r in label_runs] == [style] * len(label_runs)
    variable = runs[-1]
    assert variable.find(M + "t").text == "x"
    assert variable.find(M + "rPr/" + M + "sty") is None


def test_nested_math_font_does_not_override_explicit_inner_style():
    root = latex_to_omml(r"\mathrm{A_{\mathit{i}}}+\mathbf{\mathrm{unit}x}")
    styles = {}
    for run in root.iter(M + "r"):
        text = run.find(M + "t").text
        style = run.find(M + "rPr/" + M + "sty")
        styles[text] = None if style is None else style.get(M + "val")
        assert len(run.findall(M + "rPr")) <= 1
    assert styles["A"] == "p"
    subscript_run = root.find(M + "sSub/" + M + "sub/" + M + "r")
    assert subscript_run.find(M + "t").text == "i"
    assert subscript_run.find(M + "rPr/" + M + "sty").get(M + "val") == "i"
    assert styles["x"] == "b"
    # The label may be emitted as one run or several; its complete text stays upright.
    bold_group = list(root)[2:]
    upright = "".join(r.find(M + "t").text for item in bold_group
                      for r in item.iter(M + "r")
                      if r.find(M + "rPr/" + M + "sty").get(M + "val") == "p")
    assert upright == "unit"


def test_custom_operator_font_keeps_subscript_and_superscript_structure():
    root = latex_to_omml(r"\operatorname{softmax}_i^2(x)")
    scripts = root.find(M + "sSubSup")
    assert scripts is not None
    assert "".join(scripts.find(M + "sub").itertext()) == "i"
    assert "".join(scripts.find(M + "sup").itertext()) == "2"
    label = list(scripts.find(M + "e").iter(M + "r"))
    assert "".join(r.find(M + "t").text for r in label) == "softmax"
    assert all(r.find(M + "rPr/" + M + "sty") is not None for r in label)
    assert all(r.find(M + "rPr/" + M + "sty").get(M + "val") == "p" for r in label)


def test_text_inside_math_is_upright():
    root = latex_to_omml(r"\text{training loss}+x")
    label = root.find(M + "r")
    assert label.find(M + "t").text == "training loss"
    assert label.find(M + "rPr/" + M + "sty") is not None
    assert label.find(M + "rPr/" + M + "sty").get(M + "val") == "p"
