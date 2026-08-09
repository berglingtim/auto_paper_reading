"""讲解内容生成（脚本模式）：解析论文 → 视觉筛选关键图 → LLM 生成结构化讲解。

产出 content.json 的结构（docx 排版脚本与 SKILL.md 共用）：
{
  "title": "论文标题",
  "meta": {"journal": "...", "year": "...", "authors": "..."},
  "figures": [{"id": "fig_01", "path": "...", "caption": "...", "width_in": 6.0, "height_in": 4.0, ...}],
  "sections": [
    {"title": "一、方法灵感和发表期刊", "blocks": [
        {"type": "text", "text": "..."},
        {"type": "figure", "fig_id": "fig_02", "note": "围绕此图的讲解..."}
    ]},
    ...
  ]
}
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .models import PaperDocument

SYSTEM_PROMPT = """你是资深的 AI/计算机视觉论文讲解员，擅长把一篇论文讲得既专业又通俗。
你的任务是根据给定的论文内容，生成一份中文讲解稿，结构固定为四个部分：

一、方法灵感和发表期刊
  讲清楚：作者为什么要做这个工作（痛点/动机）；灵感来自哪些已有工作或观察；
  发表在哪个期刊/会议（给出名称与年份；若能判断，补充期刊/会议的级别信息）。

二、方法
  分模块讲清楚方法的技术细节：每个模块/组件的输入输出、核心公式的含义、
  参数与损失函数怎么设计。讲解必须图文结合：在需要的地方引用论文中的关键
  流程图/架构图/示意图（用 fig_id 引用），并围绕图里的每个模块、箭头、标注
  展开讲解。

三、输入内容的变换过程
  这是最重要也最需要细致的一节。请像追踪数据流一样讲解：
  - 输入（如一张图片）进入模型后，每一步被怎样变换：尺寸/通道数/分辨率/特征图
    大小如何变化，张量的形状如何流动；
  - 每一步"学习"了什么：哪些层/模块的参数在训练中被更新，学到了什么表征；
  - 注意力机制（如果有）是如何变化的：Q/K/V 从哪里来、attention map 的形状与
    含义、注意力权重如何随层数或训练过程演化、稀疏/稠密/多头等细节；
  - 结合流程图中的箭头与模块标识，一步步带着读者走完整条数据流。

四、创新点、可以借鉴的经验
  总结相对已有工作的核心创新点（2-5 条），以及对本领域研究者/工程师可借鉴的
  经验（如训练技巧、工程实现、损失设计、数据结构等）。

写作要求：
1. 语言：简体中文，专业术语保留英文原文（首次出现给中文释义）。
2. 结构：每部分用若干段落；图文结合时用 {"type":"figure","fig_id":"...","note":"此处讲解文字"}。
3. 内容要基于论文原文，不要编造；不确定的细节要注明"论文未明确说明"。
4. 用 JSON 输出，顶层结构为 {"title": str, "sections": [{title, blocks}]}，
   blocks 的 type 只能为 "text" 或 "figure"。
"""


def build_figure_prompt(figures: list) -> str:
    if not figures:
        return "（论文中未提取到图片）"
    lines = []
    for f in figures:
        desc = f.get("description") or ""
        sel = "【已选中用于讲解】" if f.get("selected") else "【候选】"
        lines.append(
            f"- {f['id']}（第 {f.get('page', '?')} 页，{f.get('kind', 'unknown')}）{sel}\n"
            f"  图注: {f.get('caption', '')[:200]}\n"
            f"  视觉描述: {desc[:300]}"
        )
    return "\n".join(lines)


def generate_content(
    paper: PaperDocument,
    figures_info: list[dict],
    llm,
    max_chars: int = 80_000,
) -> dict:
    """调用 LLM 生成结构化讲解内容。"""
    user_text = (
        f"请为以下论文生成讲解稿。\n\n"
        f"## 论文信息\n标题: {paper.title}\n"
        f"期刊/会议: {paper.journal} {paper.year}\n"
        f"作者: {paper.authors}\n\n"
        f"## 候选配图清单（可引用 fig_id）\n{build_figure_prompt(figures_info)}\n\n"
        f"## 论文全文\n{paper.text_for_llm(max_chars)}\n\n"
        f"请严格按系统提示的结构输出 JSON。"
    )
    raw = llm.chat(
        [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_text}],
        json_mode=True,
        temperature=0.3,
        max_tokens=8000,
    )
    return _parse_json(raw)


def _parse_json(raw: str) -> dict:
    """容忍 LLM 输出中的代码围栏/前后杂质。"""
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"LLM 未返回 JSON: {text[:300]}")
    return json.loads(text[start : end + 1])
