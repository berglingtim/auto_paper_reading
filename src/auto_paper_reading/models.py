"""跨格式统一数据模型。

解析任意格式（.pdf/.docx/.doc）后统一归约为 PaperDocument，
讲解生成与 docx 排版只依赖这一层数据。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass
class FigureRef:
    """论文中的一张图（已裁剪到本地图片文件）。

    bbox 为 PDF 页面坐标（点，point），原点在页面左上角：(x0, y0, x1, y1)。
    """

    id: str  # 形如 "fig_01"
    page: int = 0  # 1-based 页码
    bbox: Optional[tuple] = None
    caption: str = ""  # 图注全文（如 "Figure 2: The overall architecture ..."）
    image_path: str = ""  # 裁剪后的 PNG 路径
    width_in: float = 0.0  # 用于 docx 排版的图片宽度（英寸）
    height_in: float = 0.0
    kind: str = "unknown"  # flowchart / architecture / plot / photo / table / other
    selected: bool = False  # 是否被选作讲解插图
    description: str = ""  # 视觉模型对图内容的描述
    context: str = ""  # 文中引用该图的上下文（可选）


@dataclass
class Section:
    heading: str = ""
    body: str = ""
    page: int = 0


@dataclass
class PaperDocument:
    source_path: str
    title: str = ""
    authors: str = ""
    journal: str = ""  # 期刊/会议名
    year: str = ""
    abstract: str = ""
    text: str = ""  # 全文文本
    sections: list[Section] = field(default_factory=list)
    figures: list[FigureRef] = field(default_factory=list)
    format: str = ""  # pdf / docx / doc
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_dict(cls, data: dict) -> "PaperDocument":
        d = dict(data)
        d["sections"] = [Section(**s) for s in d.get("sections", [])]
        figs = []
        for f in d.get("figures", []):
            fd = dict(f)
            if fd.get("bbox") is not None:
                fd["bbox"] = tuple(fd["bbox"])
            figs.append(FigureRef(**fd))
        d["figures"] = figs
        return cls(**d)

    def text_for_llm(self, max_chars: int = 80_000) -> str:
        """返回送入 LLM 的正文文本（标题/摘要 + 截断的正文）。"""
        parts = [f"# {self.title}", f"## Abstract\n{self.abstract}"]
        body = self.text.strip()
        if len(body) > max_chars:
            body = body[:max_chars] + "\n……（正文已截断）"
        parts.append(f"## Full text\n{body}")
        return "\n\n".join(parts)
