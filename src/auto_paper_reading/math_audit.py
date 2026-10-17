"""检查交付文件中的数学标记残留，不替代渲染后的视觉复核。"""
from pathlib import Path
import re
import zipfile

from lxml import etree

from .omml import M_NS, W_NS

NS = {'m': M_NS, 'w': W_NS}
SUSPECT = re.compile(r'[_^$\ue000\ue001]|\\[A-Za-z]+')


def audit_docx(path: Path, exceptions: list[dict] | None = None) -> dict:
    """扫描正文、表格、页眉页脚，记录每个公式及已人工审核的字面文本。"""
    approved = {x['text']: x['reason'].strip() for x in (exceptions or [])
                if isinstance(x.get('text'), str) and isinstance(x.get('reason'), str)
                and x['reason'].strip()}
    report = {'docx': str(Path(path).resolve()), 'formulas': [], 'issues': [],
              'reviewed_literals': []}
    with zipfile.ZipFile(path) as z:
        parts = [n for n in z.namelist() if re.fullmatch(
            r'word/(document|header\d+|footer\d+|footnotes|endnotes)\.xml', n)]
        for part in parts:
            root = etree.fromstring(z.read(part))
            for i, para in enumerate(root.xpath('//w:p', namespaces=NS), 1):
                location = f'{part}:paragraph[{i}]'
                plain = ''.join(para.xpath('.//w:t/text()', namespaces=NS))
                if SUSPECT.search(plain):
                    if plain in approved:
                        report['reviewed_literals'].append({'location': location,
                            'text': plain, 'reason': approved[plain]})
                    else:
                        report['issues'].append({'location': location, 'text': plain,
                            'error': '普通文字中有未复核的数学标记'})
                for math in para.xpath('.//m:oMath', namespaces=NS):
                    text = ''.join(math.xpath('.//m:t/text()', namespaces=NS))
                    entry = {'location': location, 'text': text,
                             'subscripts': len(math.xpath('.//m:sub[*]', namespaces=NS)),
                             'superscripts': len(math.xpath('.//m:sup[*]', namespaces=NS))}
                    report['formulas'].append(entry)
                    if SUSPECT.search(text):
                        report['issues'].append({**entry, 'error': 'OMML 内残留数学标记'})
                    for script in math.xpath('.//m:sSub|.//m:sSup|.//m:sSubSup', namespaces=NS):
                        required = ['e'] + ({'sSub':['sub'], 'sSup':['sup'],
                            'sSubSup':['sub','sup']}[etree.QName(script).localname])
                        if any(not script.xpath(f'./m:{tag}/*', namespaces=NS) for tag in required):
                            report['issues'].append({**entry, 'error': '上下标结构缺少基底或内容'})
    report['passed'] = not report['issues']
    return report


def require_math_audit(path: Path, exceptions: list[dict] | None = None) -> dict:
    import json
    report = audit_docx(path, exceptions)
    Path(path).with_suffix('.math_audit.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    if not report['passed']:
        raise ValueError(f"数学检查失败，禁止交付：{report['issues']}")
    return report
