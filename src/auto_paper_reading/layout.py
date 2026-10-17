"""对实际渲染 PDF 做留白检查；只标记可疑页，不猜测 Word 的分页位置。"""
from pathlib import Path

import fitz


def audit_pdf(pdf_path: str | Path) -> dict:
    """以当前报告的 1in 页边距衡量文字/图片的垂直占用。

    非末页底部留白超过版心 28%，或内部空隙超过 20%，提示复核。
    末页正常短页不报警。指标只是诊断，缩图后仍须检查图中文字可读性。
    """
    pages = []
    with fitz.open(pdf_path) as document:
        for index, page in enumerate(document):
            top, bottom = 72.0, page.rect.height - 72.0
            height = bottom - top
            spans = []
            for b in page.get_text('blocks'):
                if b[3] > top and b[1] < bottom:
                    spans.append((max(top, b[1]), min(bottom, b[3])))
            # 默认文字提取不包含图像；必须单独计入实际显示的图片区域。
            for image in page.get_image_info():
                b = image['bbox']
                if b[3] > top and b[1] < bottom:
                    spans.append((max(top, b[1]), min(bottom, b[3])))
            spans.sort()
            end, largest_gap = top, 0.0
            for start, stop in spans:
                largest_gap = max(largest_gap, start - end)
                end = max(end, stop)
            blank = max(0.0, bottom - end)
            is_last = index == len(document) - 1
            pages.append({
                'page': index + 1,
                'bottom_blank_pt': round(blank, 1),
                'largest_gap_pt': round(largest_gap, 1),
                'is_last': is_last,
                'needs_review': (not is_last and blank > height * .28)
                                or largest_gap > height * .20,
            })
    return {'page_count': len(pages), 'pages': pages,
            'note': '留白提示仅供复核；检查图片、图注、标题和可读性后再调整尺寸或分页。'}
