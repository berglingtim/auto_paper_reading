"""auto_paper_reading 命令行入口。

用法示例：
  # 阶段 1：解析 + 裁剪图片（SKILL.md 工作流使用）
  python run.py papers/xxx.pdf --stage prep --out output/xxx

  # 阶段 2：视觉筛选 + LLM 生成讲解内容（需配置 API key）
  python run.py papers/xxx.pdf --stage content --out output/xxx --vision-provider kimi

  # 阶段 3：由 content.json 生成 docx
  python run.py papers/xxx.pdf --stage docx --out output/xxx

  # 全流程
  python run.py papers/xxx.pdf --stage full --out output/xxx
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import fitz  # pymupdf

# Windows 控制台默认 GBK，统一按 UTF-8 输出，避免中文乱码
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def _safe_filename(name: str, max_len: int = 80) -> str:
    """把任意字符串净化为安全的文件名（防路径分隔符/保留字符/空名）。"""
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', "_", name or "")
    name = name.strip().strip(". ")
    return (name[:max_len] or "paper")

from .docx_content import normalize_content, save_content
from .explain import generate_content
from .llm import LLMClient
from .models import PaperDocument
from .parser import parse_paper

ROOT = Path(__file__).resolve().parents[2]
BUILD_DOCX_JS = ROOT / "tools" / "build_docx.js"


def _classify_figures(figures: list, vision_client: LLMClient, max_images: int = 12) -> list[dict]:
    """用视觉模型逐张判断图片类型与是否关键，返回补全描述后的 figure 信息。"""
    prompt = (
        "这是从一篇论文中裁剪出的图片。请以 JSON 返回三个字段：\n"
        "kind: 图片类型，只能是 flowchart(流程图/架构图/示意图) / plot(实验图表) / "
        "photo(照片/真实图像) / table(表格) / other 之一；\n"
        "key: 布尔值，是否属于讲解'方法'必须配图的关键图（流程图、架构图、示意图通常为 true，"
        "实验结果图、照片通常为 false）；\n"
        "description: 一句话用中文描述图片内容（含图中可见的关键文字/标注，若有）。\n"
        '示例输出: {"kind": "flowchart", "key": true, "description": "整体架构图，包含编码器-解码器两阶段"}'
    )
    infos = []
    for f in figures[:max_images]:
        if not f.image_path or not Path(f.image_path).exists():
            continue
        try:
            raw = vision_client.chat_vision(prompt, [f.image_path], temperature=0.1)
            raw = raw.strip()
            start, end = raw.find("{"), raw.rfind("}")
            info = json.loads(raw[start : end + 1]) if start != -1 else {}
        except Exception as e:  # 单张失败不阻塞整体
            info = {}
            print(f"  [warn] 图 {f.id} 视觉分析失败: {e}")
        info.setdefault("kind", "unknown")
        info.setdefault("key", False)
        info.setdefault("description", "")
        f.kind = info["kind"]
        f.selected = bool(info["key"])
        f.description = info["description"]
        infos.append(
            {
                "id": f.id,
                "page": f.page,
                "bbox": f.bbox,
                "caption": f.caption,
                "path": f.image_path,
                "width_in": f.width_in,
                "height_in": f.height_in,
                "kind": f.kind,
                "selected": f.selected,
                "description": f.description,
            }
        )
    return infos


def _inject_math(docx_path: Path) -> int:
    """把 docx 中的 LaTeX 占位 run（\\uE000...\\uE001）替换为 OMML 公式。

    公式由 WPS/Word 打开时原生渲染；全部在 python-docx 层完成，不调用任何 Office 软件。
    """
    import docx as pydocx

    from .omml import MATH_MARK_E, MATH_MARK_S, latex_to_omml

    d = pydocx.Document(str(docx_path))
    count = 0
    for para in d.paragraphs:
        for run in list(para.runs):
            text = run.text or ""
            if not (text.startswith(MATH_MARK_S) and MATH_MARK_E in text):
                continue
            latex = text[len(MATH_MARK_S) : text.rfind(MATH_MARK_E)]
            try:
                omml = latex_to_omml(latex)
            except Exception as e:
                print(f"  [warn] 公式解析失败 {latex[:40]!r}: {e}")
                continue
            run._r.addprevious(omml)
            run._r.getparent().remove(run._r)
            count += 1
    if count:
        d.save(str(docx_path))
    return count


def _build_docx(content: dict, work_dir: Path, out_path: Path) -> Path:
    """调用 docx-js 脚本生成 docx，再注入 OMML 公式。

    目标文件被占用（如正被 WPS 打开）时自动换新文件名重试（讲解_xxx_v2.docx 等）。
    """
    content_path = save_content(content, work_dir / "content.json")
    attempt = 0
    while True:
        target = out_path if attempt == 0 else out_path.with_name(
            out_path.stem + f"_v{attempt + 1}" + out_path.suffix
        )
        cmd = ["node", str(BUILD_DOCX_JS), str(content_path), str(target)]
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("docx 生成超时（>180s）")
        if proc.returncode == 0:
            out_path = target
            break
        if "EBUSY" in (proc.stdout or "") + (proc.stderr or "") and attempt < 5:
            attempt += 1
            print(f"  [warn] 输出文件被占用（可能在 WPS 中打开），改用 {target.name}")
            continue
        raise RuntimeError(f"docx 生成失败:\n{proc.stdout}\n{proc.stderr}")
    n_math = _inject_math(out_path)
    if n_math:
        print(f"  [math] 注入 {n_math} 个 OMML 公式（WPS 原生渲染）")
    return out_path


def _check_docx_structure(docx_path: Path) -> dict:
    """不依赖任何 Office 软件的结构化校验：能打开、有段落、图片已嵌入。"""
    import zipfile

    import docx as pydocx

    d = pydocx.Document(str(docx_path))
    paras = len(d.paragraphs)
    with zipfile.ZipFile(docx_path) as z:
        media = sorted(n for n in z.namelist() if n.startswith("word/media/"))
    tables = len(d.tables)
    return {"paragraphs": paras, "tables": tables, "media": media}


def _verify_docx(docx_path: Path, work_dir: Path) -> list[Path]:
    """（可选，需显式 --verify）用 WPS 无头转换 docx→PDF 并渲染成图片检查排版。

    仅使用 kwpsconvert.exe（wpscli word2pdf，无头、不弹窗），绝不调用 wps.exe 打开 GUI。
    """
    from .parser.convert import doc_to_pdf

    verify_dir = work_dir / "verify"
    verify_dir.mkdir(parents=True, exist_ok=True)
    pdf = doc_to_pdf(docx_path, verify_dir)
    doc = fitz.open(pdf)
    imgs = []
    for pno, page in enumerate(doc):
        pix = page.get_pixmap(matrix=fitz.Matrix(110 / 72, 110 / 72), alpha=False)
        out = verify_dir / f"page_{pno + 1:02d}.png"
        pix.save(out)
        imgs.append(out)
    doc.close()
    return imgs


def _print_summary(paper: PaperDocument) -> None:
    print(f"标题: {paper.title}")
    print(f"期刊/会议: {paper.journal or '未知'}  年份: {paper.year or '未知'}")
    print(f"摘要: {paper.abstract[:200]}")
    print(f"共提取 {len(paper.figures)} 张配图:")
    for f in paper.figures:
        print(f"  - {f.id}: 第{f.page}页  {f.width_in}x{f.height_in}in  {f.caption[:80]}")


def run(args: argparse.Namespace) -> int:
    paper_path = Path(args.paper)
    if not paper_path.exists():
        print(f"[error] 论文不存在: {paper_path}", file=sys.stderr)
        return 1

    work_dir = (Path(args.out) / paper_path.stem).resolve()
    work_dir.mkdir(parents=True, exist_ok=True)

    # ---- 阶段 1：解析 + 裁剪 ----
    if args.stage in ("prep", "content", "full"):
        print(f"[1/3] 解析论文: {paper_path}")
        paper = parse_paper(paper_path, work_dir, allow_wps=getattr(args, "allow_wps", False))
        (work_dir / "paper.json").write_text(paper.to_json(), encoding="utf-8")
        _print_summary(paper)
    else:
        paper = PaperDocument.from_dict(
            json.loads((work_dir / "paper.json").read_text(encoding="utf-8"))
        )

    if args.stage == "prep":
        print(f"[done] 解析完成，产物在 {work_dir}")
        return 0

    # ---- 阶段 2：视觉筛选 + 讲解生成 ----
    content = None
    if args.stage in ("content", "full"):
        print("[2/3] 视觉筛选关键图 + LLM 生成讲解")
        vision = None
        if args.vision_provider != "none":
            try:
                vision = LLMClient("vision")
            except RuntimeError as e:
                print(f"  [warn] {e}")
        if vision is not None:
            figures_info = _classify_figures(paper.figures, vision)
        else:
            figures_info = [
                {
                    "id": f.id, "page": f.page, "caption": f.caption, "path": f.image_path,
                    "width_in": f.width_in, "height_in": f.height_in,
                    "kind": f.kind, "selected": f.selected, "description": f.description,
                }
                for f in paper.figures
            ]
        if args.text_provider != "none":
            try:
                llm = LLMClient("text")
            except RuntimeError as e:
                print(f"[error] {e}", file=sys.stderr)
                return 1
            content = generate_content(paper, figures_info, llm, max_chars=args.max_chars)
            content.setdefault("figures", figures_info)
            content["meta"] = {
                "journal": paper.journal,
                "year": paper.year,
                "authors": paper.authors,
                "source": str(paper_path),
            }
            content = normalize_content(content, work_dir)
            save_content(content, work_dir / "content.json")
            print(f"[done] 讲解内容已生成: {work_dir / 'content.json'}")
        else:
            print("[warn] 未配置文本模型（--text-provider none），跳过讲解生成。请由 agent 手写 content.json。")

    if args.stage == "content":
        return 0

    # ---- 阶段 3：生成 docx ----
    if args.stage in ("docx", "full"):
        print("[3/3] 生成 docx")
        content_path = work_dir / "content.json"
        if not content_path.exists():
            print(f"[error] 缺少 {content_path}，请先生成讲解内容", file=sys.stderr)
            return 1
        content = normalize_content(json.loads(content_path.read_text(encoding="utf-8")), work_dir)
        out_name = f"讲解_{_safe_filename(paper.title or paper_path.stem)}.docx"
        out_docx = work_dir / out_name
        out_docx = _build_docx(content, work_dir, out_docx)
        print(f"[done] docx 已生成: {out_docx}")
        # 默认只做结构化校验（不调用任何 Office 软件）
        try:
            check = _check_docx_structure(out_docx)
            print(
                f"[check] 结构校验通过：{check['paragraphs']} 段、{check['tables']} 表、"
                f"{len(check['media'])} 张嵌入图片"
            )
        except Exception as e:
            print(f"[warn] 结构校验失败: {e}")
        # 视觉渲染预览需显式 --verify（会调用 WPS 无头转换，不弹窗）
        if getattr(args, "verify", False):
            try:
                pages = _verify_docx(out_docx, work_dir)
                print(f"[verify] 渲染 {len(pages)} 页预览图到 {work_dir / 'verify'}")
            except Exception as e:
                print(f"[warn] 渲染预览失败: {e}")
        return 0

    print(f"[error] 未知阶段: {args.stage}", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="auto_paper_reading：论文 → 图文讲解 docx")
    parser.add_argument("paper", help="论文路径（.pdf/.docx/.doc）")
    parser.add_argument("--out", default="output", help="输出目录（默认 output/）")
    parser.add_argument(
        "--stage",
        choices=["prep", "content", "docx", "full"],
        default="full",
        help="执行到哪个阶段：prep=解析裁剪 / content=+生成讲解 / docx=+排版 / full=全流程",
    )
    parser.add_argument("--text-provider", choices=["deepseek", "kimi", "openai", "none"], default="none")
    parser.add_argument("--vision-provider", choices=["kimi", "openai", "none"], default="none")
    parser.add_argument("--max-chars", type=int, default=80_000, help="送入 LLM 的正文最大字符数")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="生成 docx 后用 WPS 无头转换渲染预览图（默认只做结构化校验，不调用 Office 软件）",
    )
    parser.add_argument(
        "--allow-wps",
        action="store_true",
        help="允许调用 WPS 无头转换（kwpsconvert.exe word2pdf）解析 .doc/.docx 输入。"
        "默认关闭；注意部分安全软件可能对办公软件自动化行为误报，请自行判断。",
    )
    args = parser.parse_args(argv)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
