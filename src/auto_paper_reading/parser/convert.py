"""Local Word-to-PDF conversion: LibreOffice by default, WPS only when selected."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import fitz

# 环境变量可覆盖自动查找结果
_ENV_KEY = "WPS_CONVERT"

# 查找结果缓存：WPS 安装位置在进程生命周期内不变，避免每次转换重复扫盘
_WPS_CACHE: Path | None | bool = None   # None=未查找, False=未找到, Path=已找到


def find_libreoffice() -> Path | None:
    """Find the console entry point without starting an office application."""
    configured = os.environ.get("LIBREOFFICE_PATH")
    if configured:
        candidate = Path(configured).expanduser()
        if not candidate.is_file():
            raise RuntimeError(
                f"LIBREOFFICE_PATH 不是可执行文件 / not an executable file: {candidate}"
            )
        return candidate.resolve()
    names = ("soffice.com", "soffice.exe") if sys.platform == "win32" else (
        ("soffice", "libreoffice") if sys.platform == "darwin" else ("libreoffice", "soffice")
    )
    for name in names:
        found = shutil.which(name)
        if found:
            return Path(found)
    if sys.platform == "win32":
        roots = [
            Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "LibreOffice/program",
            Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "LibreOffice/program",
            Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local"))) / "Programs/LibreOffice/program",
        ]
    elif sys.platform == "darwin":
        roots = [Path("/Applications/LibreOffice.app/Contents/MacOS"),
                 Path.home() / "Applications/LibreOffice.app/Contents/MacOS"]
    else:
        roots = [Path("/usr/bin"), Path("/usr/local/bin")]
    return next((root / name for root in roots for name in names if (root / name).is_file()), None)


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


def doc_to_pdf(src: Path, out_dir: Path, timeout: int = 180, *, backend: str = "libreoffice") -> Path:
    """Convert using short temporary paths, validate, then publish atomically.

    Office never sees the user's deep input/output paths. LibreOffice uses
    an isolated profile in the system temporary directory for every call.
    The validated PDF is copied to a temporary file beside the destination
    before replacement, so publication also works across filesystems.
    No GUI, remote
    service, default-app changes, or automatic fallback to WPS are involved.
    """
    if backend not in ("libreoffice", "wps"):
        raise ValueError(f"Unsupported PDF backend: {backend!r}")
    src = Path(src).resolve()
    if not src.is_file():
        raise FileNotFoundError(src)
    if src.suffix.lower() not in (".doc", ".docx"):
        raise ValueError(f"Word input must be .doc or .docx: {src}")
    exe = find_libreoffice() if backend == "libreoffice" else find_wps_convert()
    if exe is None:
        if backend == "libreoffice":
            raise RuntimeError(
                "未找到 LibreOffice / LibreOffice not found. "
                "Install the free LibreOffice Writer from https://www.libreoffice.org/download/ "
                "or set LIBREOFFICE_PATH to soffice.com (Windows) / soffice (macOS/Linux). "
                "WPS is optional and is never selected automatically."
            )
        raise RuntimeError(
            "未找到可选 WPS 转换器 / Optional WPS converter not found. "
            "Set WPS_CONVERT to kwpsconvert.exe, or use --pdf-backend libreoffice."
        )
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{src.stem}.pdf"
    with tempfile.TemporaryDirectory(prefix="apr-", ignore_cleanup_errors=True) as temporary:
        stage = Path(temporary)
        local_src = stage / ("input" + src.suffix.lower())
        shutil.copyfile(src, local_src)
        converted = stage / "input.pdf"
        if backend == "libreoffice":
            profile = (stage / "p").as_uri()
            cmd = [str(exe), f"-env:UserInstallation={profile}",
                   "--headless", "--nologo", "--nodefault", "--norestore",
                   "--convert-to", "pdf:writer_pdf_Export", "--outdir", str(stage), str(local_src)]
        else:
            cmd = [str(exe), "word2pdf", str(local_src), "-o", str(converted)]
        try:
            proc = subprocess.run(
                cmd, cwd=stage, capture_output=True, text=True, timeout=timeout,
                encoding="utf-8", errors="replace",
                **({"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}),
            )
        except subprocess.TimeoutExpired as error:
            raise RuntimeError(f"{backend} conversion timed out after {timeout}s / 转换超时") from error
        except OSError as error:
            raise RuntimeError(f"Cannot start {backend} converter / 无法启动转换器: {error}") from error
        if proc.returncode != 0 or not converted.is_file():
            detail = (proc.stdout or "") + (proc.stderr or "")
            raise RuntimeError(f"{backend} conversion failed / 转换失败 ({proc.returncode}): {detail.strip()[:500]}")
        try:
            with fitz.open(stream=converted.read_bytes(), filetype="pdf") as pdf:
                if not pdf.is_pdf or pdf.needs_pass or len(pdf) == 0:
                    raise ValueError("PDF is empty, encrypted, or not a PDF")
        except Exception as error:
            raise RuntimeError(f"{backend} produced an invalid PDF / PDF 无效: {error}") from error
        publication = None
        try:
            with tempfile.NamedTemporaryFile(prefix=".apr-", suffix=".pdf",
                                             dir=out_dir, delete=False) as target:
                publication = Path(target.name)
                with converted.open("rb") as source:
                    shutil.copyfileobj(source, target)
            publication.replace(out)
        finally:
            if publication is not None:
                publication.unlink(missing_ok=True)
    return out
