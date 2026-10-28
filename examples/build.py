"""Build both layout examples through the project's normal OMML and audit pipeline."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from auto_paper_reading.cli import _build_docx, _verify_docx


def main() -> None:
    parser = argparse.ArgumentParser(description="生成中英文排版示例 / Build bilingual layout examples")
    parser.add_argument("--out", type=Path, default=ROOT / "output" / "examples")
    parser.add_argument("--verify", action="store_true", help="Render using the selected PDF backend (default: LibreOffice)")
    parser.add_argument("--pdf-backend", choices=("libreoffice", "wps"), default="libreoffice")
    args = parser.parse_args()
    for language, filename in [("zh", "讲解_排版示例.docx"), ("en", "Explanation_Layout Example.docx")]:
        source = ROOT / "examples" / language / "content.json"
        content = json.loads(source.read_text(encoding="utf-8"))
        work = (args.out / language).resolve()
        work.mkdir(parents=True, exist_ok=True)
        report = _build_docx(content, work, work / filename)
        print(report)
        if args.verify:
            _verify_docx(report, work, language, pdf_backend=args.pdf_backend)


if __name__ == "__main__":
    main()
