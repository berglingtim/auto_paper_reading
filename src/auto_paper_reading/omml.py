r"""LaTeX → OMML（Office Math Markup Language）转换器。

把 content.json 文本中 `$...$` 包裹的 LaTeX 公式转换为 OMML 元素，
嵌入 docx 后由兼容办公软件原生渲染为公式（非图片、非纯文本）。

要点：
- OMML 没有 <m:group> 元素（WPS 会丢弃其内容），因此 `{...}` 组一律
  "展开"为父容器（m:e / m:num / m:den / m:sub / m:sup / oMath）的直接子元素。
- 支持子集：上下标（含组合）、\frac、\sum/\prod/\int（带上下限）、\sqrt、
  \left...\right 定界符、希腊字母、\mathbb/\mathbf、\hat/\bar/\vec、
  \log/\max 等函数、常用符号（\cdot \times \odot \in \to 等）、\text{}。
"""

from __future__ import annotations

import re

from lxml import etree

M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_M = f"{{{M_NS}}}"
_W = f"{{{W_NS}}}"
_XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"

GREEK = {
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε",
    "zeta": "ζ", "eta": "η", "theta": "θ", "iota": "ι", "kappa": "κ",
    "lambda": "λ", "mu": "μ", "nu": "ν", "xi": "ξ", "omicron": "ο",
    "pi": "π", "rho": "ρ", "sigma": "σ", "tau": "τ", "upsilon": "υ",
    "phi": "φ", "chi": "χ", "psi": "ψ", "omega": "ω",
    "Gamma": "Γ", "Delta": "Δ", "Theta": "Θ", "Lambda": "Λ", "Xi": "Ξ",
    "Pi": "Π", "Sigma": "Σ", "Phi": "Φ", "Psi": "Ψ", "Omega": "Ω",
}

SYMBOLS = {
    "cdot": "⋅", "cdotp": "·", "times": "×", "odot": "⊙", "circ": "∘",
    "pm": "±", "mp": "∓", "ast": "∗", "star": "⋆", "div": "÷",
    "to": "→", "rightarrow": "→", "leftarrow": "←", "mapsto": "↦",
    "in": "∈", "notin": "∉", "ni": "∋",
    "le": "≤", "leq": "≤", "ge": "≥", "geq": "≥", "ne": "≠", "neq": "≠",
    "approx": "≈", "sim": "∼", "propto": "∝", "equiv": "≡", "cong": "≅",
    "infty": "∞", "partial": "∂", "nabla": "∇", "emptyset": "∅",
    "forall": "∀", "exists": "∃", "neg": "¬", "land": "∧", "lor": "∨",
    "subset": "⊂", "supset": "⊃", "subseteq": "⊆", "supseteq": "⊇",
    "cup": "∪", "cap": "∩", "setminus": "∖", "oplus": "⊕", "otimes": "⊗",
    "angle": "∠", "perp": "⊥", "parallel": "∥", "therefore": "∴",
    "because": "∵", "ldots": "…", "cdots": "⋯", "dots": "…",
    "prime": "′", "degree": "°", "ell": "ℓ", "hbar": "ℏ",
    "quad": " ", "qquad": "  ", ",": " ", ";": " ", "!": "", ":": " ",
}

NARY = {"sum": "∑", "prod": "∏", "int": "∫", "oint": "∮",
        "bigcup": "⋃", "bigcap": "⋂", "bigoplus": "⊕"}

FUNCS = {
    "log", "exp", "max", "min", "sin", "cos", "tan", "cot", "sec", "csc",
    "arcsin", "arccos", "arctan", "ln", "det", "lim", "inf", "sup", "arg",
    "dim", "ker", "Pr", "gcd", "deg", "sigmoid", "Re", "Im",
}

ACCENTS = {"hat": "\u0302", "bar": "\u0304", "vec": "\u20D7",
           "dot": "\u0307", "ddot": "\u0308", "tilde": "\u0303"}

_CMD_RE = re.compile(r"[A-Za-z]+")


class LatexError(ValueError):
    pass


def _elem(tag: str, **attrs) -> etree._Element:
    el = etree.Element(_M + tag)
    for k, v in attrs.items():
        el.set(_M + k, v)
    return el


def _run(text: str, sty: str | None = None) -> etree._Element:
    """创建 m:r 文本 run。sty: p(plain)/b(bold)/i(italic)/bi。"""
    r = _elem("r")
    if sty:
        rpr = etree.SubElement(r, _M + "rPr")
        s = etree.SubElement(rpr, _M + "sty")
        s.set(_M + "val", sty)
    # 西文/数字统一 Times New Roman；公式变量斜体由 OMML 默认数学样式保留
    wrpr = etree.SubElement(r, _W + "rPr")
    rfonts = etree.SubElement(wrpr, _W + "rFonts")
    rfonts.set(_W + "ascii", "Times New Roman")
    rfonts.set(_W + "hAnsi", "Times New Roman")
    t = etree.SubElement(r, _M + "t")
    t.text = text
    t.set(_XML_SPACE, "preserve")
    return r


def _fill(container: etree._Element, items: list) -> None:
    for it in items:
        container.append(it)


class LatexParser:
    """递归下降解析器：把 LaTeX 解析为 OMML 元素。

    解析结果以 list[etree._Element] 表示"一组兄弟元素"：
    - `{...}` 组返回其中全部子元素（不创建 m:group 包装）
    - 单个字符/命令返回单元素列表
    - parse_item 负责把组整体包进上下标（m:e 可容纳多个子元素）
    """

    def __init__(self, latex: str):
        self.s = latex
        self.i = 0
        self.cur: list = []  # 当前正在填充的兄弟元素列表

    # ---- 基础工具 ----
    def peek(self) -> str:
        return self.s[self.i] if self.i < len(self.s) else ""

    def next(self) -> str:
        ch = self.s[self.i]
        self.i += 1
        return ch

    def skip_ws(self):
        # 空串 in 任意字符串恒为 True，必须先判空，否则死循环
        while self.peek() and self.peek() in " \t":
            self.i += 1

    # ---- 解析 ----
    def parse(self) -> etree._Element:
        root = _elem("oMath")
        items = self.parse_seq(None)
        _fill(root, items)
        return root

    def parse_seq(self, stop: str | None) -> list:
        """解析到 stop 字符为止，返回这一段的兄弟元素列表。"""
        saved = self.cur
        self.cur = []
        while self.peek() and self.peek() != stop:
            self.cur.extend(self.parse_item())
        out = self.cur
        self.cur = saved
        return out

    def parse_group(self) -> list:
        """解析一个操作数（返回元素列表）：{...}、单个字符、或命令。"""
        self.skip_ws()
        ch = self.peek()
        if not ch:
            raise LatexError(f"公式意外结束: …{self.s[max(0, self.i - 20):self.i]}…")
        if ch == "{":
            self.next()
            items = self.parse_seq("}")
            if self.peek() != "}":
                raise LatexError(f"缺少右括号: …{self.s[max(0, self.i - 15):self.i + 15]}…")
            self.next()
            return items
        if ch == "\\":
            return self.parse_command()
        if ch in ("_", "^", "}"):
            raise LatexError(f"缺少基底或多余标记: {ch!r}，位置 {self.i}")
        if ch == " ":
            self.next()
            return []
        return [_run(self.next())]

    def parse_command(self) -> list:
        self.next()  # 吃掉反斜杠
        m = _CMD_RE.match(self.s, self.i)
        if not m:
            cmd = self.next()  # 单字符命令，如 \{ \| \; \, \! \ （转义空格）
            if cmd in ("{", "}", "|"):
                return [_run(cmd)]
            if cmd == " ":
                return [_run(" ")]  # \ 转义空格 → 普通空格
            if cmd in SYMBOLS:
                return [_run(SYMBOLS[cmd])]
            return [_run("\\" + cmd)]
        cmd = m.group(0)
        self.i = m.end()

        if cmd in GREEK:
            return [_run(GREEK[cmd])]
        if cmd in SYMBOLS:
            return [_run(SYMBOLS[cmd])]
        if cmd in ACCENTS:
            base = self.parse_group()
            acc = _elem("acc")
            pr = etree.SubElement(acc, _M + "accPr")
            c = etree.SubElement(pr, _M + "chr")
            c.set(_M + "val", ACCENTS[cmd])
            e = etree.SubElement(acc, _M + "e")
            _fill(e, base)
            return [acc]
        if cmd in NARY:
            return [self.parse_nary(NARY[cmd])]
        if cmd == "frac":
            num = self.parse_group()
            den = self.parse_group()
            f = _elem("f")
            n = etree.SubElement(f, _M + "num")
            _fill(n, num)
            d = etree.SubElement(f, _M + "den")
            _fill(d, den)
            return [f]
        if cmd == "sqrt":
            rad = _elem("rad")
            pr = etree.SubElement(rad, _M + "radPr")
            if self.peek() == "[":
                self.next()
                deg = self.parse_seq("]")
                self.next()
                dg = etree.SubElement(rad, _M + "deg")
                _fill(dg, deg)
            else:
                hide = etree.SubElement(pr, _M + "degHide")
                hide.set(_M + "val", "1")
                etree.SubElement(rad, _M + "deg")
            base = self.parse_group()
            e = etree.SubElement(rad, _M + "e")
            _fill(e, base)
            return [rad]
        if cmd == "left":
            return [self.parse_delimiter()]
        if cmd in ("mathbb", "mathbf", "mathrm", "operatorname", "mathit"):
            base = self.parse_group()
            if cmd in ("mathbb", "mathbf"):
                for it in base:
                    for r in it.iter(_M + "r"):
                        rpr = etree.SubElement(r, _M + "rPr")
                        sty = etree.SubElement(rpr, _M + "sty")
                        sty.set(_M + "val", "b")
            return base
        if cmd == "text":
            if self.peek() == "{":
                self.next()
                start = self.i
                depth = 1
                while self.i < len(self.s) and depth:
                    if self.s[self.i] == "{":
                        depth += 1
                    elif self.s[self.i] == "}":
                        depth -= 1
                    self.i += 1
                return [_run(self.s[start : self.i - 1])]
            raise LatexError("\\text 需要 {…}")
        if cmd in FUNCS:
            name = self.parse_scripts([_run(cmd, sty="p")])
            arg = self.parse_item() if self.peek() and self.peek() not in ")}]" else []
            func = _elem("func")
            fn = etree.SubElement(func, _M + "fName")
            _fill(fn, name)
            e = etree.SubElement(func, _M + "e")
            _fill(e, arg)
            return [func]
        raise LatexError(f"不支持的 LaTeX 命令: \\{cmd}")

    def parse_nary(self, chr_: str) -> etree._Element:
        nary = _elem("nary")
        pr = etree.SubElement(nary, _M + "naryPr")
        c = etree.SubElement(pr, _M + "chr")
        c.set(_M + "val", chr_)
        lim = etree.SubElement(pr, _M + "limLoc")
        lim.set(_M + "val", "undOvr")
        sub = etree.SubElement(nary, _M + "sub")
        sup = etree.SubElement(nary, _M + "sup")
        if self.peek() == "_":
            self.next()
            _fill(sub, self.parse_group())
        if self.peek() == "^":
            self.next()
            _fill(sup, self.parse_group())
        e = etree.SubElement(nary, _M + "e")
        _fill(e, self.parse_group())
        return nary

    def parse_delimiter(self) -> etree._Element:
        r"""\left X ... \right Y → m:d 定界符。"""
        beg = self.parse_delim_char()
        inner = self.parse_seq_until_right()
        end = self.parse_delim_char()
        d = _elem("d")
        if beg or end:
            dpr = etree.SubElement(d, _M + "dPr")
            if beg:
                b = etree.SubElement(dpr, _M + "begChr")
                b.set(_M + "val", beg)
            if end:
                e = etree.SubElement(dpr, _M + "endChr")
                e.set(_M + "val", end)
        e = etree.SubElement(d, _M + "e")
        _fill(e, inner)
        return d

    def parse_seq_until_right(self) -> list:
        r"""解析 \left...\right 之间的内容，遇到 \right 停止并消费之。"""
        out = []
        while True:
            if not self.peek():
                raise LatexError("\\left 缺少 \\right")
            if self.peek() == "\\":
                m2 = _CMD_RE.match(self.s, self.i + 1)
                if m2 and m2.group(0) == "right":
                    self.i = m2.end()
                    break
            out.extend(self.parse_item())
        return out

    def parse_delim_char(self) -> str:
        self.skip_ws()
        if self.peek() == "\\":
            m = _CMD_RE.match(self.s, self.i + 1)
            if m and m.group(0) in ("|", "langle", "rangle", "lbrace", "rbrace"):
                self.i = m.end()
                return {"|": "|", "langle": "⟨", "rangle": "⟩",
                        "lbrace": "{", "rbrace": "}"}[m.group(0)]
            if m and m.group(0) == "right":
                return ""
        ch = self.next()
        return {"(": "(", ")": ")", "[": "[", "]": "]", "{": "{",
                "}": "}", "|": "|", ".": ""}.get(ch, "")

    def parse_item(self) -> list:
        base = self.parse_group()
        return self.parse_scripts(base)

    def parse_scripts(self, base: list) -> list:
        sub = sup = None
        self.skip_ws()
        while self.peek() in ("^", "_"):  # 空串 in 字符串恒为 True，须用元组
            op = self.next()
            if op == "^":
                if sup is not None:
                    raise LatexError("重复上标，请使用花括号明确结构")
                sup = self.parse_group()
            else:
                if sub is not None:
                    raise LatexError("重复下标，请使用花括号明确结构")
                sub = self.parse_group()
            self.skip_ws()
        if sub is None and sup is None:
            return base
        ss = _elem("sSubSup" if (sub is not None and sup is not None)
                   else ("sSup" if sup is not None else "sSub"))
        e = etree.SubElement(ss, _M + "e")
        _fill(e, base)
        if sub is not None:
            sb = etree.SubElement(ss, _M + "sub")
            _fill(sb, sub)
        if sup is not None:
            sp = etree.SubElement(ss, _M + "sup")
            _fill(sp, sup)
        return [ss]


def latex_to_omml(latex: str) -> etree._Element:
    """把一段 LaTeX 转换为 <m:oMath> 元素。"""
    latex = latex.strip()
    if not latex:
        raise LatexError("空公式")
    result = LatexParser(latex).parse()
    # 每条公式独立核对，不能用别处的上下标替这条公式“通过检查”。
    for marker, tag in (("_", "sub"), ("^", "sup")):
        actual = sum(bool(len(el)) for el in result.iter(_M + tag))
        if actual != latex.count(marker):
            raise LatexError(f"{marker} 结构数量不匹配：源码 {latex.count(marker)}，OMML {actual}")
    if any(re.search(r"[_^]", el.text or "") for el in result.iter(_M + "t")):
        raise LatexError("公式中残留未转换的 _ 或 ^")
    return result


MATH_MARK = ("\uE000", "\uE001")  # 私有区字符，docx-js 生成的占位标记
MATH_MARK_S, MATH_MARK_E = MATH_MARK
