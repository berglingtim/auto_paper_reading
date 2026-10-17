import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH

from auto_paper_reading.cli import _build_docx


def test_body_and_figure_explanation_are_justified(tmp_path):
    content = {'title': '排版测试', 'sections': [{'title': '方法', 'blocks': [
        {'type': 'text', 'text': '正文内容'},
        {'type': 'figure', 'fig_id': 'missing', 'note': '图后讲解'},
    ]}]}
    d = docx.Document(_build_docx(content, tmp_path, tmp_path/'layout.docx'))
    for text in ['正文内容', '图后讲解']:
        p = next(p for p in d.paragraphs if p.text == text)
        assert p.alignment == WD_ALIGN_PARAGRAPH.JUSTIFY
    assert d.paragraphs[0].alignment == WD_ALIGN_PARAGRAPH.CENTER


def test_equations_are_separate_numbered_and_preserve_surrounding_text(tmp_path):
    content = {'sections': [{'title': '方法', 'blocks': [
        {'type': 'text', 'text': '前文$x^2$后文。\n$$\ny = 2x\n$$'},
        {'type': 'equation', 'latex': r'z=\frac{1}{2}'},
    ]}, {'title': '变换', 'blocks': [
        {'type': 'figure', 'fig_id': 'missing', 'note': '说明$a+b$结束'},
    ]}]}
    for name in ['first.docx', 'second.docx']:
        d = docx.Document(_build_docx(content, tmp_path, tmp_path/name))
        eqs = [p for p in d.paragraphs if p._p.xpath('./m:oMath')]
        assert len(eqs) == 4
        assert [p.text.strip() for p in eqs] == ['（1）', '（2）', '（3）', '（4）']
        assert all(len(p.paragraph_format.tab_stops) == 2 for p in eqs)
        texts = [p.text for p in d.paragraphs]
        assert all(t in texts for t in ['前文', '后文。', '说明', '结束'])
        assert '\ue000' not in d._element.xml
