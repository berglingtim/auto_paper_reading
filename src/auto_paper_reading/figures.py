"""从 PDF 中提取并裁剪论文配图（关键流程图等）。

三条提取路径：
1. 光栅图：用 `page.get_images() + get_image_rects()` 获取图片的真实放置位置
   （正确处理旋转/镜像图片，其 dict bbox 可能倒置）。
2. 矢量图合并：同一图被切成多个图片块时（子图行、分片），按垂直/水平相邻合并。
3. 矢量图形（流程图/架构图，无嵌入图片）：按"图注（Figure N / 图 N）"定位，
   用图注上方同列内的绘图对象（drawings）与图片块并集确定图形区域；
   无矢量内容时退回"最近文本边界"策略。

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
MERGE_GAP = 12.0  # 相邻图片块的合并间距阈值


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


def _norm_rect(box) -> tuple:
    """规范化 bbox：旋转/镜像图片的 bbox 可能 y0>y1 或 x0>x1。"""
    x0, y0, x1, y1 = box[0], box[1], box[2], box[3]
    return (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


def _boxes_overlap(a: tuple, b: tuple) -> bool:
    return max(a[0], b[0]) < min(a[2], b[2]) and max(a[1], b[1]) < min(a[3], b[3])


def _merge_boxes(boxes: list[list]) -> list[list]:
    """合并相邻图块：垂直相邻（同列上下拼接）或水平相邻（同行左右子图）。

    每个 box 为 [x0, y0, x1, y1, caption?]，合并时保留已有图注。
    """
    if not boxes:
        return []
    boxes = sorted(boxes, key=lambda b: (b[1], b[0]))
    merged: list[list] = [list(boxes[0])]
    for b in boxes[1:]:
        last = merged[-1]
        x_overlap = min(last[2], b[2]) - max(last[0], b[0])
        y_overlap = min(last[3], b[3]) - max(last[1], b[1])
        v_gap = b[1] - last[3]
        h_gap = b[0] - last[2]
        if (x_overlap > 0 and v_gap < MERGE_GAP) or (y_overlap > 0 and h_gap < MERGE_GAP):
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


def _vector_content_bbox(
    drawings: list,
    image_rects: list,
    c_top: float,
    col_x0: float,
    col_x1: float,
    page: "fitz.Page",
    regions: list[list] | None = None,
) -> tuple | None:
    """图注上方同列内绘图对象（+图片块）的并集 bbox，用于定位矢量图形。

    正文通常没有绘图对象，因此并集能覆盖到矢量图（方框/箭头/连线）的完整范围。
    跳过整列宽的细横线（常见于栏目分隔线），跳过已被既有图区域覆盖的内容。
    drawings/image_rects 由调用方按页缓存，避免每条图注重复解析。
    """
    page_w, page_h = page.rect.width, page.rect.height
    top, bottom, left, right = page_h, 0.0, col_x1, col_x0
    found = False

    def inside_region(x, y) -> bool:
        for r in regions or []:
            if r[0] <= x <= r[2] and r[1] <= y <= r[3]:
                return True
        return False

    def absorb(rect):
        nonlocal top, bottom, left, right, found
        r = _norm_rect(rect)
        # 限制在页面内
        x0, y0 = max(0.0, r[0]), max(0.0, r[1])
        x1, y1 = min(page_w, r[2]), min(page_h, r[3])
        if y1 > c_top or y1 < page_h * HEADER_FOOTER_RATIO:
            return
        if y0 >= c_top:
            return
        if x1 <= col_x0 or x0 >= col_x1:  # 不在本列
            return
        # 跳过整列宽的细横线（栏目分隔线）：高度 < 2pt 且宽度 > 列宽 60%
        col_w = col_x1 - col_x0
        if (y1 - y0) < 2.0 and (x1 - x0) > col_w * 0.6:
            return
        # 跳过过小装饰（点/小图标）
        if (y1 - y0) * (x1 - x0) < 4.0:
            return
        # 跳过已被既有图区域覆盖的内容（避免矢量带吃掉相邻图）
        if inside_region((x0 + x1) / 2, (y0 + y1) / 2):
            return
        top, bottom = min(top, y0), max(bottom, y1)
        left, right = min(left, x0), max(right, x1)
        found = True

    for d in drawings:
        absorb(d["rect"])
    for rect in image_rects:
        absorb(rect)

    if not found:
        return None
    return (left, top, right, bottom)


def _caption_region(
    caption: dict,
    text_blocks: list[dict],
    regions: list[list],
    page: "fitz.Page",
    page_w: float,
    page_h: float,
    drawings: list | None = None,
    image_rects: list | None = None,
) -> tuple:
    """由一条图注推导图形区域 bbox。

    策略：优先用图注上方同列内的矢量内容并集（精确定位矢量图）；
    无矢量内容时退回"最近文本块/已有区域边界"扩展。
    """
    cbox = caption["bbox"]
    c_top, c_bottom = cbox[1], cbox[3]
    x0, x1 = _column_xrange(cbox, text_blocks, page_w)

    content = _vector_content_bbox(drawings or [], image_rects or [], c_top, x0, x1, page, regions)
    if content:
        cx0, cy0, cx1, cy1 = content
        col_w = x1 - x0
        # 内容宽度远超列宽 → 跨栏大图，放宽 x 范围；否则贴合列宽
        if (cx1 - cx0) > col_w * 1.5:
            x0, x1 = max(0, min(x0, cx0 - 5)), min(page_w, max(x1, cx1 + 5))
        else:
            x0, x1 = max(x0, cx0 - 5), min(x1, cx1 + 5)
        return (x0, max(0, cy0 - 5), x1, c_top - 2)

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
    out_dir = Path(out_dir).resolve()
    pdf_path = Path(pdf_path).resolve()
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"输入必须是 PDF 文件: {pdf_path}")
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF 不存在: {pdf_path}")
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

        # 1) 光栅图区域（真实放置位置；过滤旋转图产生的越界/压正文的误框）
        text_area = [
            b["bbox"]
            for b in blocks
            if b["type"] == 0 and not _is_header_footer(b["bbox"], page_h)
        ]
        raster: list[list] = []
        for img_xref in page.get_images(full=True):
            for rect in page.get_image_rects(img_xref[0]):
                x0, y0, x1, y1 = _norm_rect(rect)
                x0, x1 = max(0.0, x0), min(page_w, x1)
                y0, y1 = max(0.0, y0), min(page_h, y1)
                w, h = x1 - x0, y1 - y0
                if w < MIN_REGION_W or h < MIN_REGION_H:
                    continue
                # 整页背景图跳过
                if w > page_w * 0.95 and h > page_h * 0.95:
                    continue
                # 超过一半面积压在正文文字上 → 旋转/镜像导致的误框，跳过
                overlap = 0.0
                for tb in text_area:
                    o_w = min(x1, tb[2]) - max(x0, tb[0])
                    o_h = min(y1, tb[3]) - max(y0, tb[1])
                    if o_w > 0 and o_h > 0:
                        overlap += o_w * o_h
                if overlap > w * h * 0.5:
                    continue
                raster.append([x0, y0, x1, y1, ""])
        raster = _merge_boxes(raster)

        # 2) 图注 → 矢量图形区域（仅当图注附近没有光栅图时）
        # 每页只解析一次绘图对象与图片放置位置（较重），供所有图注复用
        page_drawings = page.get_drawings()
        page_image_rects = [
            rect for img_xref in page.get_images(full=True) for rect in page.get_image_rects(img_xref[0])
        ]
        captions = [(b, _block_text(b)) for b in text_blocks if _is_caption(b)]
        regions = [list(r) for r in raster]
        for cb, ct in captions:
            cbx0, cby0, cbx1, _ = cb["bbox"]
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
            regions.append(
                [
                    *_caption_region(
                        cb, text_blocks, regions, page, page_w, page_h,
                        drawings=page_drawings, image_rects=page_image_rects,
                    ),
                    ct,
                ]
            )

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
