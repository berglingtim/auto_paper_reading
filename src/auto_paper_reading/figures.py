"""从 PDF 中提取并裁剪论文配图（关键流程图等）。

两条提取路径：
1. 光栅图：直接读取页面上嵌入的图片块（pymupdf dict 中 type=1 的 block），
   合并垂直相邻/重叠的碎片，过滤页眉页脚、小图标、整页背景图。
2. 矢量图：许多论文的流程图是矢量绘制（无嵌入图片块），
   通过"图注（Figure N / 图 N）"定位：向上（或向下）扩展到最近文本块/已有图区域，
   得到图注所属列内的图形区域并裁剪。

裁剪结果保存为 PNG，并附带图注、尺寸、页码等信息，供视觉模型筛选与 docx 排版。
"""

from __future__ import annotations

import re
from pathlib import Path

import fitz  # pymupdf

from .models import FigureRef

# 图注正则：匹配 "Figure 2:", "Fig. 3", "图 4" 等开头
CAPTION_RE = re.compile(
    r"^\s*(?:(?:Fig(?:ure|\.)?\.?)\s*[:：]?\s*(\d+)|(?:图)\s*[:：]?\s*(\d+))", re.IGNORECASE
)
TABLE_RE = re.compile(r"^\s*(?:Table|表)\s*\d+", re.IGNORECASE)
# 页眉页脚判定：页面高度上下 5% 之内的文本视为页眉页脚
HEADER_FOOTER_RATIO = 0.05
# 图注与图区域的最大间距（点）
CAPTION_GAP = 150.0
MIN_REGION_W = 50.0  # 最小区域宽（点），更小的视为图标/装饰
MIN_REGION_H = 30.0


def _block_text(block: dict) -> str:
    return " ".join(
        span["text"] for line in block.get("lines", []) for span in line.get("spans", [])
    ).strip()


def _is_caption(block: dict) -> bool:
    t = _block_text(block)
    return bool(CAPTION_RE.match(t)) and not TABLE_RE.match(t)


def _is_header_footer(bbox: tuple, page_h: float) -> bool:
    y0, y1 = bbox[1], bbox[3]
    return y1 < page_h * HEADER_FOOTER_RATIO or y0 > page_h * (1 - HEADER_FOOTER_RATIO)


def _merge_boxes(boxes: list[list]) -> list[list]:
    """合并 x 有重叠且垂直间距小的 box（同一图被切成多块的情况）。

    每个 box 为 [x0, y0, x1, y1, caption?]，合并时保留已有图注。
    """
    if not boxes:
        return []
    boxes = sorted(boxes, key=lambda b: (b[1], b[0]))
    merged: list[list] = [list(boxes[0])]
    for b in boxes[1:]:
        last = merged[-1]
        x_overlap = min(last[2], b[2]) - max(last[0], b[0])
        gap = b[1] - last[3]
        if x_overlap > 0 and gap < 10:
            last[0] = min(last[0], b[0])
            last[1] = min(last[1], b[1])
            last[2] = max(last[2], b[2])
            last[3] = max(last[3], b[3])
            if len(last) > 4 and not last[4] and len(b) > 4:
                last[4] = b[4]
        else:
            merged.append(list(b))
    return merged


def _column_xrange(caption_bbox: tuple, text_blocks: list[dict], page_w: float) -> tuple:
    """估计图注所在列的水平范围 [x0, x1]（处理单栏/双栏）。"""
    cx0, cx1 = caption_bbox[0], caption_bbox[2]
    xs, x1s = [cx0], [cx1]
    for b in text_blocks:
        bb = b["bbox"]
        # 与图注 x 范围有重叠的文本块视为同列
        if max(bb[0], cx0) < min(bb[2], cx1) and (bb[3] - bb[1]) > 8:
            xs.append(bb[0])
            x1s.append(bb[2])
    x0, x1 = min(xs), max(x1s)
    # 双栏情形下避免跨列：若列宽明显大于页宽的 3/4，按页边距保守放宽
    if (x1 - x0) > page_w * 0.75:
        x0 = max(0, cx0 - 30)
        x1 = min(page_w, cx1 + 30)
    return x0, x1


def _caption_region(
    caption: dict,
    text_blocks: list[dict],
    regions: list[list],
    page_w: float,
    page_h: float,
) -> tuple:
    """由一条图注推导矢量图形区域 bbox。

    优先向上扩展（多数论文图在注上方）；若上方空间过小则向下扩展。
    扩展边界 = 同列内最近的文本块边界 / 已有图区域边界（不跨过它们）。
    """
    cbox = caption["bbox"]
    c_top, c_bottom = cbox[1], cbox[3]
    x0, x1 = _column_xrange(cbox, text_blocks, page_w)

    def nearest_above() -> float:
        best = 0.0
        for tb in text_blocks:
            bb = tb["bbox"]
            if _is_header_footer(bb, page_h) or tb is caption:
                continue
            if bb[3] <= c_top and max(bb[0], x0) < min(bb[2], x1):
                best = max(best, bb[3])
        for r in regions:
            if r[3] <= c_top and max(r[0], x0) < min(r[2], x1):
                best = max(best, r[3])
        return best

    def nearest_below() -> float:
        best = page_h
        for tb in text_blocks:
            bb = tb["bbox"]
            if _is_header_footer(bb, page_h) or tb is caption:
                continue
            if bb[1] >= c_bottom and max(bb[0], x0) < min(bb[2], x1):
                best = min(best, bb[1])
        for r in regions:
            if r[1] >= c_bottom and max(r[0], x0) < min(r[2], x1):
                best = min(best, r[1])
        return best

    top_region = (x0, nearest_above() + 2, x1, c_top - 2)
    bottom_region = (x0, c_bottom + 2, x1, nearest_below() - 2)
    # 选择面积更大的一侧
    a_top = (top_region[3] - top_region[1]) * (top_region[2] - top_region[0])
    a_bottom = (bottom_region[3] - bottom_region[1]) * (bottom_region[2] - bottom_region[0])
    return top_region if a_top >= a_bottom else bottom_region


def extract_figures(
    pdf_path: str | Path,
    out_dir: str | Path,
    dpi: int = 200,
    max_figures: int = 40,
) -> list[FigureRef]:
    """从 PDF 提取全部配图区域并裁剪为 PNG。

    Returns:
        list[FigureRef]：含 id/page/bbox/caption/image_path/width_in/height_in。
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)
    full_text = "\n".join(page.get_text("text") for page in doc)

    figures: list[FigureRef] = []
    scale = dpi / 72.0

    for pno, page in enumerate(doc):
        page_h = page.rect.height
        page_w = page.rect.width
        blocks = page.get_text("dict")["blocks"]
        text_blocks = [b for b in blocks if b["type"] == 0]
        img_blocks = [b for b in blocks if b["type"] == 1]

        # 1) 光栅图区域
        raster: list[list] = []
        for b in img_blocks:
            x0, y0, x1, y1 = b["bbox"]
            w, h = x1 - x0, y1 - y0
            if w < MIN_REGION_W or h < MIN_REGION_H:
                continue
            # 整页背景图跳过
            if w > page_w * 0.95 and h > page_h * 0.95:
                continue
            raster.append([x0, y0, x1, y1, ""])
        raster = _merge_boxes(raster)

        # 2) 图注 → 矢量图区域（仅当图注附近没有光栅图时）
        captions = [(b, _block_text(b)) for b in text_blocks if _is_caption(b)]
        regions = [list(r) for r in raster]
        for cb, ct in captions:
            cbx0, cby0, cbx1, _ = cb["bbox"]
            # 图注紧贴在已有区域（光栅图）下方：把图注绑定到该区域
            attached = False
            for r in regions:
                if (
                    abs(r[3] - cby0) < CAPTION_GAP
                    and r[1] < cby0
                    and max(r[0], cbx0) < min(r[2], cbx1)
                ):
                    if not r[4]:
                        r[4] = ct
                    attached = True
            if attached:
                continue
            # 否则按图注推导矢量图形区域
            regions.append([*_caption_region(cb, text_blocks, regions, page_w, page_h), ct])

        # 3) 合并重叠区域并过滤
        regions = _merge_boxes(regions)
        regions = [
            r
            for r in regions
            if (r[2] - r[0]) >= MIN_REGION_W
            and (r[3] - r[1]) >= MIN_REGION_H
            and not ((r[2] - r[0]) > page_w * 0.95 and (r[3] - r[1]) > page_h * 0.95)
        ]

        # 4) 裁剪 + 图注兜底匹配
        for x0, y0, x1, y1, *rest in regions:
            if len(figures) >= max_figures:
                break
            clip = fitz.Rect(x0, y0, x1, y1)
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=clip, alpha=False)
            if pix.width < 80 or pix.height < 60:  # 过滤过小的产物
                continue
            idx = len(figures) + 1
            img_path = out_dir / f"fig_{idx:02d}_p{pno + 1}.png"
            pix.save(img_path)

            caption = rest[0] if rest else ""
            if not caption:  # 兜底：按距离找最近图注（优先下方）
                best, best_dist = "", CAPTION_GAP + 1
                for cb, ct in captions:
                    cbb = cb["bbox"]
                    below, above = cbb[1] - y1, y0 - cbb[3]
                    if below >= 0:
                        d = below
                    elif above >= 0:
                        d = above + CAPTION_GAP  # 稍惩罚"上方图注"
                    else:
                        continue
                    if d < best_dist:
                        best_dist, best = d, ct
                caption = best

            figures.append(
                FigureRef(
                    id=f"fig_{idx:02d}",
                    page=pno + 1,
                    bbox=(round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)),
                    caption=caption,
                    image_path=str(img_path),
                    width_in=round((x1 - x0) / 72.0, 2),
                    height_in=round((y1 - y0) / 72.0, 2),
                    context=_find_context(full_text, caption),
                )
            )
        if len(figures) >= max_figures:
            break

    doc.close()
    return figures


def _find_context(full_text: str, caption: str, radius: int = 200) -> str:
    """在正文中查找图注对应编号的引用上下文。"""
    m = CAPTION_RE.match(caption)
    if not m:
        return ""
    num = m.group(1) or m.group(2)
    if not num:
        return ""
    for pat in (rf"Figure\s*{num}", rf"Fig(?:ure)?\.?\s*{num}", rf"图\s*{num}"):
        for mm in re.finditer(pat, full_text, re.IGNORECASE):
            start = max(0, mm.start() - radius)
            end = min(len(full_text), mm.end() + radius)
            ctx = re.sub(r"\s+", " ", full_text[start:end]).strip()
            if ctx:
                return ctx
    return ""
