"""content.json 的读写与规范化（docx 排版脚本与 SKILL.md 共用的中间格式）。"""

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
