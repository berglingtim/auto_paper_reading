"""把 .doc / .docx 等 Word 文档转换为 PDF（借助 WPS Office）。

WPS 的 kwpsconvert.exe（即 wpscli）提供 word2pdf 子命令，
这是本机可用的唯一 Office 软件，无需额外安装。
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

# 环境变量可覆盖自动查找结果
_ENV_KEY = "WPS_CONVERT"

# 查找结果缓存：WPS 安装位置在进程生命周期内不变，避免每次转换重复扫盘
_WPS_CACHE: Path | None | bool = None   # None=未查找, False=未找到, Path=已找到


def find_wps_convert() -> Path | None:
    """在常见安装位置查找 kwpsconvert.exe（wpscli 入口），结果进程内缓存。"""
    global _WPS_CACHE
    if _WPS_CACHE is not None:
        return _WPS_CACHE or None
    env = os.environ.get(_ENV_KEY)
    if env and Path(env).exists():
        _WPS_CACHE = Path(env)
        return _WPS_CACHE

    home = Path.home()
    roots = [
        home / "AppData" / "Local" / "Kingsoft" / "WPS Office",
        Path("C:/Program Files (x86)/Kingsoft"),
        Path("C:/Program Files/Kingsoft"),
    ]
    exe_names = ("kwpsconvert.exe", "wpscli.exe")
    for root in roots:
        if root.exists():
            # WPS Office/<version>/office6/... 或 Kingsoft/office6/...
            for cand in (root, *root.iterdir()):
                if not cand.is_dir():
                    continue
                od = cand if cand.name == "office6" else cand / "office6"
                for name in exe_names:
                    p = od / name
                    if p.exists():
                        _WPS_CACHE = p
                        return p
    _WPS_CACHE = False
    return None


def doc_to_pdf(src: Path, out_dir: Path, timeout: int = 180) -> Path:
    """把 Word 文档转换为 PDF，返回生成的 PDF 路径。

    Raises:
        RuntimeError: 找不到 WPS 或转换失败。
    """
    src = Path(src)
    out_dir = Path(out_dir)
    exe = find_wps_convert()
    if exe is None:
        raise RuntimeError(
            "未找到 WPS Office（kwpsconvert.exe / wpscli.exe），无法转换 .doc/.docx。\n"
            "请确认已安装 WPS Office，或用环境变量 WPS_CONVERT 指定转换程序路径。"
        )

    # wpscli 会把相对路径解析到自身安装目录，必须用绝对路径
    src = src.resolve()
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{src.stem}.pdf"
    # 清理同名旧产物，避免 wpscli 自动改名导致返回路径不存在
    if out.exists():
        out.unlink()
    cmd = [str(exe), "word2pdf", str(src), "-o", str(out)]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0 or not out.exists():
        detail = (proc.stdout or "") + (proc.stderr or "")
        raise RuntimeError(f"WPS 转换失败（{proc.returncode}）：{detail.strip()[:500]}")
    return out
