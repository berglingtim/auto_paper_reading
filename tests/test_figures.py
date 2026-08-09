"""figures.py 纯函数单元测试。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from auto_paper_reading.figures import (  # noqa: E402
    CAPTION_RE,
    _is_caption,
    _merge_boxes,
    _norm_rect,
)


def _box(x0, y0, x1, y1, cap=""):
    return [x0, y0, x1, y1, cap]


def test_norm_rect_flipped():
    # 旋转/镜像图片的 bbox 可能倒置
    assert _norm_rect((73, 279, 300, 192)) == (73, 192, 300, 279)
    assert _norm_rect((300, 100, 100, 200)) == (100, 100, 300, 200)


def test_merge_vertical_adjacent():
    boxes = [_box(0, 0, 100, 50), _box(0, 55, 100, 100)]
    merged = _merge_boxes(boxes)
    assert len(merged) == 1
    assert merged[0][:4] == [0, 0, 100, 100]


def test_merge_horizontal_subplots():
    # 同一行左右相邻的子图应合并为一个图
    boxes = [_box(0, 0, 100, 60), _box(105, 0, 205, 60), _box(210, 0, 310, 60)]
    merged = _merge_boxes(boxes)
    assert len(merged) == 1
    assert merged[0][:4] == [0, 0, 310, 60]


def test_no_merge_far_apart():
    boxes = [_box(0, 0, 100, 50), _box(0, 200, 100, 250)]
    assert len(_merge_boxes(boxes)) == 2


def test_caption_regex():
    cases = [
        ("Figure 1. The architecture", True),
        ("Fig. 2: Results", True),
        ("Fig 3 results", True),
        ("Figure 10: Ablation", True),
        ("图 4 整体架构", True),
        ("Table 1. Comparison", False),  # 表格图注不算配图
        ("1 Introduction", False),
        ("Abstract", False),
    ]
    for text, expected in cases:
        block = {"lines": [{"spans": [{"text": text}]}]}
        assert _is_caption(block) is expected, text
        assert bool(CAPTION_RE.match(text)) is expected, text
