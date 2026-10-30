"""Check formula typography at the actual Office/PDF boundary when available."""
import re

import docx
import fitz
import pytest

from auto_paper_reading.omml import latex_to_omml
from auto_paper_reading.parser.convert import doc_to_pdf, find_libreoffice


def test_installed_libreoffice_keeps_labels_upright_and_variables_italic(tmp_path):
    if find_libreoffice() is None:
        pytest.skip("LibreOffice is not installed")
    document = docx.Document()
    paragraph = document.add_paragraph()
    paragraph._p.append(latex_to_omml(
        r"\mathrm{Attention}(x)+\operatorname{customop}_i^2(x)+\text{training loss}"))
    source = tmp_path / "math.docx"
    document.save(source)
    pdf = doc_to_pdf(source, tmp_path / "render")
    with fitz.open(pdf) as result:
        spans = [s for b in result[0].get_text("dict")["blocks"]
                 for line in b.get("lines", []) for s in line["spans"]]
    for label in ("Attention", "customop", "training", "loss"):
        matches = [s for s in spans if label in s["text"]]
        assert matches, f"Label missing or incorrectly spaced: {label}"
        assert all(not s["flags"] & 2 for s in matches), f"Label became italic: {label}"
    variables = [s for s in spans if re.search(r"\bx\b", s["text"])]
    assert variables and all(s["flags"] & 2 for s in variables)
