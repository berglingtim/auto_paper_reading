"""content.json 的读写与规范化（docx 排版脚本与 SKILL.md 共用的中间格式）。

新报告在顶层提供 abstract（非空中文摘要）和 symbols（符号对象数组）。
排版顺序为标题/元信息 → 摘要 → 符号表 → sections，前置部分不占正文标题编号。
symbols 项：symbol、meaning 必填；shape、role、source 表示类型/维度、作用、出处/范围。
只列核心、反复出现或易混淆的符号；简单临时变量就近解释。空数组表示无须集中列示。
旧输入省略前置字段仍兼容，不自动生成研究内容。
原生表格块：{"type":"table", "headers":["方法","核心"], "rows":[["A","描述"]],
"column_weights":[1,3]}。每行与表头等长，权重可省略，单元格支持换行和行内公式。
原生表格为黑白三线表：顶/底线 1.5pt，表头下线 0.75pt，全单元格水平/垂直居中。
正文三级编号采用 一 / 1.1 / 1.1.1，前置标题不编号。

公式块使用 {"type": "equation", "latex": "y = Wx + b"}，不带分隔符或编号。
排版器负责独立成行及全文连续编号；text/note 中 $...$ 为不编号的行内公式，
$$...$$ 为独立编号公式。
图片默认等比缩小；layout.max_figure_height_in/max_figure_width_in 为全局上限，
figure 条目或 block 的 max_height_in/max_width_in 可覆盖。章节和 block 支持
page_break_before；独立 page_break 块在下一实际内容前分页。
"""

from __future__ import annotations

import json
from pathlib import Path


def save_content(content: dict, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_content(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def normalize_content(content: dict, base_dir: str | Path | None = None) -> dict:
    """补齐字段：figures 中缺省的尺寸/路径，sections 中缺省结构。

    base_dir 用于把 figures[].path 处理为相对路径（位于 base_dir 内时转相对、
    保持相对路径原样），保证 content.json 可随仓库迁移、跨机器使用。
    """
    base = Path(base_dir).resolve() if base_dir else None
    content.setdefault("figures", [])
    for f in content["figures"]:
        f.setdefault("caption", "")
        f.setdefault("width_in", 6.0)
        f.setdefault("height_in", 4.0)
        if base and f.get("path"):
            p = Path(f["path"])
            if p.is_absolute():
                try:  # 位于工作目录内 → 存相对路径（可移植）
                    f["path"] = str(p.resolve().relative_to(base)).replace("\\", "/")
                except ValueError:  # 工作目录外 → 保留绝对路径
                    pass
    content.setdefault("sections", [])
    for sec in content["sections"]:
        sec.setdefault("title", "")
        sec.setdefault("blocks", [])
    return content
