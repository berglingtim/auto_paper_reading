r"""LaTeX → OMML（Office Math Markup Language）转换器。

把 content.json 文本中 `$...$` 包裹的 LaTeX 公式转换为 OMML 元素，
嵌入 docx 后由 WPS/Word 原生渲染为公式（非图片、非纯文本）。

支持子集：上下标（含组合）、\frac、\sum/\prod/\int（带上下限）、\sqrt、
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

DELIM = {"(": "(", ")": ")", "[": "[", "]": "]", "{": "{", "}": "}",
         "|": "|", "\\|": "|", ".": ""}

_CMD_RE = re.compile(r"[A-Za-z]+")


class LatexError(ValueError):
    pass


def _elem(tag: str, **attrs) -> etree._Element:
    el = etree.Element(_M + tag)
    for k, v in attrs.items():
        el.set(_M + k, v)
    return el


def _run(text: str, bold: bool = False) -> etree._Element:
    r = _elem("r")
    if bold:
        rpr = etree.SubElement(r, _M + "rPr")
        sty = etree.SubElement(rpr, _M + "sty")
        sty.set(_M + "val", "b")
    t = etree.SubElement(r, _M + "t")
    t.text = text
    t.set(_XML_SPACE, "preserve")
    return r


class LatexParser:
    """递归下降解析器：把 LaTeX 字符串解析为 OMML 元素树。"""

    def __init__(self, latex: str):
        self.s = latex
        self.i = 0
        self.cur: etree._Element | None = None

    # ---- 基础工具 ----
    def peek(self) -> str:
        return self.s[self.i] if self.i < len(self.s) else ""

    def next(self) -> str:
        ch = self.s[self.i]
        self.i += 1
        return ch

    def skip_ws(self):
        # 注意: 空串 in 任意字符串 恒为 True，必须先用 peek() 判空
        while self.peek() and self.peek() in " \t":
            self.i += 1

    # ---- 解析 ----
    def parse(self) -> etree._Element:
        root = _elem("oMath")
        self.cur = root
        self.parse_seq(None)
        return root

    def parse_seq(self, stop: str | None):
        while self.peek() and self.peek() != stop:
            item = self.parse_item()
            if item is not None:
                self.cur.append(item)

    def parse_group(self) -> etree._Element:
        """解析一个操作数：{...}、单个字符、或命令（如 \frac、\alpha）。"""
        self.skip_ws()
        ch = self.peek()
        if not ch:
            raise LatexError(f"公式意外结束: …{self.s[max(0, self.i - 20):self.i]}…")
        if ch == "{":
            self.next()
            g = _elem("group")
            saved, self.cur = self.cur, g
            self.parse_seq("}")
            self.cur = saved
            if self.peek() != "}":
                raise LatexError(f"缺少右括号: …{self.s[max(0, self.i - 15):self.i + 15]}…")
            self.next()
            return g
        if ch == "\\":
            return self.parse_command()
        if ch == " ":
            self.next()
            return None
        return _run(self.next())

    def parse_command(self) -> etree._Element:
        self.next()  # 吃掉反斜杠
        m = _CMD_RE.match(self.s, self.i)
        if not m:
            cmd = self.next()  # 单字符命令，如 \{ \| \; \, \!
            if cmd in DELIM:
                return _run(cmd)
            if cmd in SYMBOLS:
                return _run(SYMBOLS[cmd])
            return _run("\\" + cmd)
        cmd = m.group(0)
        self.i = m.end()

        if cmd in GREEK:
            return _run(GREEK[cmd])
        if cmd in SYMBOLS:
            return _run(SYMBOLS[cmd])
        if cmd in ACCENTS:
            base = self.parse_group()
            acc = _elem("acc")
            pr = etree.SubElement(acc, _M + "accPr")
            c = etree.SubElement(pr, _M + "chr")
            c.set(_M + "val", ACCENTS[cmd])
            e = etree.SubElement(acc, _M + "e")
            e.append(base)
            return acc
        if cmd in NARY:
            return self.parse_nary(NARY[cmd])
        if cmd == "frac":
            num = self.parse_group()
            den = self.parse_group()
            f = _elem("f")
            n = etree.SubElement(f, _M + "num")
            n.append(num)
            d = etree.SubElement(f, _M + "den")
            d.append(den)
            return f
        if cmd == "sqrt":
            rad = _elem("rad")
            pr = etree.SubElement(rad, _M + "radPr")
            if self.peek() == "[":
                self.next()
                deg = self.parse_seq_until("]")
                self.next()
                dg = etree.SubElement(rad, _M + "deg")
                dg.append(deg)
            else:
                hide = etree.SubElement(pr, _M + "degHide")
                hide.set(_M + "val", "1")
                etree.SubElement(rad, _M + "deg")
            base = self.parse_group()
            e = etree.SubElement(rad, _M + "e")
            e.append(base)
            return rad
        if cmd == "left":
            return self.parse_delimiter()
        if cmd in ("mathbb", "mathbf", "mathrm", "operatorname", "mathit"):
            base = self.parse_group()
            if cmd in ("mathbb", "mathbf"):
                for r in base.iter(_M + "r"):
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
                return _run(self.s[start : self.i - 1])
            raise LatexError("\\text 需要 {…}")
        if cmd in FUNCS:
            arg = self.parse_group()
            func = _elem("func")
            fn = etree.SubElement(func, _M + "fName")
            fn.append(_run(cmd, bold=True))
            e = etree.SubElement(func, _M + "e")
            e.append(arg)
            return func
        raise LatexError(f"不支持的 LaTeX 命令: \\{cmd}")

    def parse_seq_until(self, stop: str) -> etree._Element:
        g = _elem("group")
        saved, self.cur = self.cur, g
        self.parse_seq(stop)
        self.cur = saved
        return g

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
            sub.append(self.parse_group())
        if self.peek() == "^":
            self.next()
            sup.append(self.parse_group())
        e = etree.SubElement(nary, _M + "e")
        e.append(self.parse_group())
        return nary

    def parse_delimiter(self) -> etree._Element:
        r"""\left X ... \right Y → m:d 定界符。"""
        beg = self.parse_delim_char()
        inner = _elem("group")
        saved, self.cur = self.cur, inner
        while True:
            if not self.peek():
                raise LatexError("\\left 缺少 \\right")
            if self.peek() == "\\":
                m2 = _CMD_RE.match(self.s, self.i + 1)
                if m2 and m2.group(0) == "right":
                    self.i = m2.end()
                    break
            item = self.parse_item()
            if item is not None:
                inner.append(item)
        self.cur = saved
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
        e.append(inner)
        return d

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
        return DELIM.get(ch, "")

    def parse_item(self) -> etree._Element:
        base = self.parse_group()
        sub = sup = None
        while self.peek() in ("^", "_"):  # 注意: 不能用字符串成员判断，空串恒为真
            op = self.next()
            if op == "^":
                sup = self.parse_group()
            else:
                sub = self.parse_group()
        if sub is None and sup is None:
            return base
        ss = _elem("sSubSup" if (sub is not None and sup is not None)
                   else ("sSup" if sup is not None else "sSub"))
        e = etree.SubElement(ss, _M + "e")
        e.append(base)
        if sub is not None:
            sb = etree.SubElement(ss, _M + "sub")
            sb.append(sub)
        if sup is not None:
            sp = etree.SubElement(ss, _M + "sup")
            sp.append(sup)
        return ss


def latex_to_omml(latex: str) -> etree._Element:
    """把一段 LaTeX 转换为 <m:oMath> 元素。"""
    latex = latex.strip()
    if not latex:
        raise LatexError("空公式")
    return LatexParser(latex).parse()


MATH_MARK = ("\uE000", "\uE001")  # 私有区字符，docx-js 生成的占位标记
MATH_MARK_S, MATH_MARK_E = MATH_MARK


def wrap_math_marker(latex: str) -> str:
    return MATH_MARK[0] + latex + MATH_MARK[1]
