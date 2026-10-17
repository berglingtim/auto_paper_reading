"""逐公式结构检查 + 对应 PDF 残留检查；不能代替逐页视觉复核。"""
import argparse
import json
from pathlib import Path
import re
import sys

import fitz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from auto_paper_reading.math_audit import audit_docx


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target', help='明确的 DOCX 路径，或仅含一个 DOCX 的目录')
    args = parser.parse_args(argv)
    target = Path(args.target).resolve()
    if target.is_dir():
        candidates = list(target.glob('*.docx'))
        if len(candidates) != 1:
            parser.error('目录中没有唯一 DOCX；请指定需要交付的具体版本文件')
        target = candidates[0]
    if not target.is_file() or target.suffix.lower() != '.docx':
        parser.error('请指定存在的 DOCX 文件')
    content = target.parent / 'content.json'
    exceptions = json.loads(content.read_text(encoding='utf-8')).get('math_review_exceptions', []) if content.exists() else []
    report = audit_docx(target, exceptions)
    pdfs = [p for p in (target.parent/'verify'/f'{target.stem}.pdf', target.with_suffix('.pdf')) if p.exists()]
    if len(pdfs) != 1:
        report['issues'].append({'error': '未找到唯一同名 PDF；请重新渲染指定 DOCX'})
    else:
        pdf = pdfs[0]
        report['pdf'] = str(pdf)
        if pdf.stat().st_mtime < target.stat().st_mtime:
            report['issues'].append({'error': 'PDF 早于 DOCX，请重新渲染'})
        with fitz.open(pdf) as document:
            report['page_count'] = len(document)
            for page_no, page in enumerate(document, 1):
                for line in page.get_text().splitlines():
                    if re.search(r'[_^\ue000\ue001]|\\[A-Za-z]+', line):
                        literal = next((x for x in exceptions if x.get('reason', '').strip()
                            and line.strip() and line.strip() in x.get('text', '')), None)
                        if literal is None:
                            report['issues'].append({'page': page_no, 'text': line,
                                                     'error': 'PDF 有未复核的数学标记残留'})
    report['passed'] = not report['issues']
    out = target.with_suffix('.math_audit.json')
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"公式数: {len(report['formulas'])}；问题数: {len(report['issues'])}；报告: {out}")
    for issue in report['issues']:
        print(issue)
    if report['passed']:
        print('自动检查通过；仍须逐页视觉检查公式的上下标位置、基底与可读性。')
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
    sys.exit(main())
