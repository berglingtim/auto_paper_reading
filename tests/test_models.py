"""数据模型测试：序列化往返与 LLM 文本截断。"""

import json

from auto_paper_reading.models import FigureRef, PaperDocument, Section


def test_paper_document_round_trip():
    paper = PaperDocument(
        source_path="a.pdf",
        title="Transformer",
        sections=[Section(heading="1 Intro", body="hello", page=1)],
        figures=[FigureRef(id="fig_01", page=2, bbox=(10, 20, 300, 200), caption="Figure 1: x")],
    )
    d = paper.to_dict()
    assert d["title"] == "Transformer"

    # JSON 往返
    paper2 = PaperDocument.from_dict(json.loads(paper.to_json()))
    assert paper2.title == paper.title
    assert paper2.sections[0].heading == "1 Intro"
    assert paper2.figures[0].id == "fig_01"
    assert paper2.figures[0].bbox == (10, 20, 300, 200)
    assert isinstance(paper2.figures[0].bbox, tuple)


def test_text_for_llm_truncation():
    paper = PaperDocument(source_path="a.pdf", title="T", abstract="ab", text="x" * 100_000)
    out = paper.text_for_llm(max_chars=1000)
    assert len(out) < 5_000
    assert "截断" in out
