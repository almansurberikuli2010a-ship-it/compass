"""Compass step checker.

How it works (the "repair test"):
  1. Compare every line with the line before it ("checks follow your previous line").
  2. If every part of the relation changed in the same way (same number added to all
     parts, or all parts multiplied by the same number), the step is correct.
  3. Otherwise try to explain the change with ONE known mistake. The first mistake whose
     "wrong version" of the previous line equals the student's line gets named.
Because step 2 and 3 use exact algebra (SymPy), "certain" really means proved.
"""
from __future__ import annotations

import re
import string
from dataclasses import dataclass, field

import sympy as sp
from sympy.parsing.sympy_parser import (convert_xor, implicit_multiplication_application,
                                        parse_expr, standard_transformations)

from . import taxonomy

_T = standard_transformations + (implicit_multiplication_application, convert_xor)
_NS = {c: sp.Symbol(c) for c in string.ascii_letters}  # every letter is a plain variable
_REL = re.compile(r"(<=|>=|=|<|>)")
_TASK = re.compile(r"^\s*(solve|find|simplify|calculate|evaluate|expand)\b\s*:?\s*", re.I)
_FLIP = {"<": ">", "<=": ">=", ">": "<", ">=": "<=", "=": "="}
_FAMILY = {"mm": "len", "cm": "len", "dm": "len", "m": "len", "km": "len",
           "mg": "mass", "g": "mass", "kg": "mass", "ml": "vol", "l": "vol"}
_UNIT = re.compile(r"(?<![A-Za-z])\d*\.?\d*\s*(mm|cm|dm|km|mg|kg|ml|m|g|l)(?![A-Za-z])")

HINTS = {
    "arithmetic_slip": "One number in this step looks slightly off. Try the calculation again, slowly.",
    "copy_error": "A number changed while copying. Compare this line with the one above it.",
    "distribution": "The number outside the brackets multiplies every term inside, not just the first.",
    "unlike_terms": "These terms don't match (different letters or powers), so they can't be combined yet.",
    "dropped_term": "A term from the line above is missing here. Compare the two lines.",
    "inequality_flip": "Multiplying or dividing by a negative number flips the inequality sign.",
    "order_of_ops": "Multiplication and division come before addition and subtraction.",
    "equals_sign": "'=' means 'is the same as'. Try writing each result on its own line.",
    "unit_mistake": "These amounts use different units. Convert to one unit before combining them.",
    "messy_layout": "The lines wander across the page, so the steps are hard to follow. Try one step under the other.",
    "numeric_sign": "Look at the signs in this calculation. One of them may have flipped.",
    "check": "This line doesn't seem to follow from the one above. Try redoing the step from the previous line.",
}


@dataclass
class Mistake:
    type: str
    certainty: str = "certain"  # "certain" = proved with algebra, "likely" = heuristic
    hint: str = ""
    practice: str | None = None
    also: list[str] = field(default_factory=list)

    def to_dict(self):
        return {"type": self.type, "name": taxonomy.name(self.type), "certainty": self.certainty,
                "hint": self.hint, "practice": self.practice,
                "also": [{"type": a, "name": taxonomy.name(a)} for a in self.also]}


@dataclass
class LineIn:
    text: str
    box: list[float] | None = None          # [x, y, w, h] as fractions of the photo
    unclear: list[dict] = field(default_factory=list)  # [{"pos": 4, "alternatives": ["1", "7"]}]


@dataclass
class Step:
    index: int
    text: str
    status: str = "ok"                      # ok | check | unreadable | unchecked
    box: list[float] | None = None
    mistake: Mistake | None = None
    unclear: list[dict] = field(default_factory=list)

    def to_dict(self):
        return {"index": self.index, "text": self.text, "status": self.status, "line_box": self.box,
                "mistake": self.mistake.to_dict() if self.mistake else None, "unreadable": self.unclear}


@dataclass
class Rel:
    text: str
    texts: list[str]
    parts: list[sp.Expr]   # evaluated (used for maths)
    raw: list[sp.Expr]     # not evaluated (keeps brackets, used to see *how* it was written)
    ops: list[str]


# ----------------------------------------------------------------------------- parsing
def _norm(s: str) -> str:
    for a, b in (("−", "-"), ("–", "-"), ("—", "-"), ("×", "*"), ("·", "*"), ("÷", "/"),
                 ("²", "^2"), ("³", "^3"), ("≤", "<="), ("≥", ">=")):
        s = s.replace(a, b)
    return re.sub(r"(?<=\d)\s*[xX]\s*(?=\d)", "*", s).strip()  # "7 x 8" means 7*8


def _p(s: str, evaluate: bool = True):
    return parse_expr(s, local_dict=_NS, transformations=_T, evaluate=evaluate)


def parse_line(text: str) -> Rel | None:
    s = _norm(text)
    if re.search(r"[A-Za-z]{4,}", s):  # real words are not algebra ("hello" would become h*e*l*l*o)
        return None
    pieces = _REL.split(s)
    texts, ops = [p.strip() for p in pieces[0::2]], pieces[1::2]
    if not texts or not all(texts):
        return None
    try:
        parts = [_p(t) for t in texts]
    except Exception:
        return None
    try:
        raw = [_p(t, False) for t in texts]
    except Exception:
        raw = parts
    return Rel(s, texts, parts, raw, ops)


def _same(a, b) -> bool:
    d = sp.expand(a - b)
    return d == 0 or sp.simplify(d) == 0


def _num(e) -> bool:
    return getattr(e, "is_number", False)


# ----------------------------------------------------------------------------- wording
def _desc(kind: str, v) -> str:
    if kind == "add":
        return f"{'adding' if v > 0 else 'subtracting'} {abs(v)}"
    if v.is_Rational and v.p == 1:
        return f"dividing by {v.q}"
    return f"multiplying by {v}"


def _practice(P: Rel, kind: str, v) -> str | None:
    if len(P.parts) != 2:
        return None
    a, b, r = P.texts[0], P.texts[1], P.ops[0]
    if kind == "add":
        s = "+" if v > 0 else "-"
        return f"{a} {s} {abs(v)} {r} {b} {s} __"
    if v.is_Rational and v.p == 1:
        return f"({a}) ÷ {v.q} {r} ({b}) ÷ __"
    return f"({a}) × {v} {r} ({b}) × __"


# ----------------------------------------------------------------------------- correct steps
def _common_op(P: Rel, C: Rel):
    """Did every part change the same way?  ("add", k) or ("mul", k) or None."""
    if len(P.parts) < 2:
        return None
    adds = [sp.expand(c - p) for p, c in zip(P.parts, C.parts)]
    if all(_same(adds[0], a) for a in adds[1:]):
        return ("add", adds[0])
    if all(p != 0 for p in P.parts):
        muls = [sp.simplify(c / p) for p, c in zip(P.parts, C.parts)]
        if all(_same(muls[0], m) for m in muls[1:]):
            return ("mul", muls[0])
    return None


def _solutions_match(P: Rel, C: Rel) -> bool:
    """Fallback for correct jumps: both lines are equations with the same solutions."""
    if P.ops != ["="] or C.ops != ["="]:
        return False
    syms = set().union(*[e.free_symbols for e in P.parts + C.parts])
    if len(syms) != 1:
        return False
    x = next(iter(syms))
    try:
        return (sp.solveset(P.parts[0] - P.parts[1], x, sp.S.Reals)
                == sp.solveset(C.parts[0] - C.parts[1], x, sp.S.Reals))
    except Exception:
        return False


def _inequality(P: Rel, C: Rel, com):
    kind, v = com
    if all(o == "=" for o in P.ops):
        return None if C.ops == P.ops else _generic()
    neg = kind == "mul" and _num(v) and bool(v < 0)
    if C.ops == ([_FLIP[o] for o in P.ops] if neg else P.ops):
        return None
    if neg and C.ops == P.ops:
        return Mistake("inequality_flip", "certain", HINTS["inequality_flip"])
    return _generic()


# ----------------------------------------------------------------------------- "wrong versions"
def _dist_variants(raw):
    """k(a+b) written as ka+b  (distribution reached only the first term)."""
    out, terms = [], sp.Add.make_args(raw)
    for i, t in enumerate(terms):
        adds = [f for f in t.args if f.is_Add] if t.is_Mul else []
        if adds:
            rest = sp.Mul(*[f for f in t.args if f is not adds[0]])
            a = sp.Add.make_args(adds[0])
            others = sum((sp.expand(u) for j, u in enumerate(terms) if j != i), sp.Integer(0))
            out.append(sp.expand(rest * a[0] + sp.Add(*a[1:]) + others))
    return out


def _unlike_variants(expr):
    """Two terms with different letters/powers merged:  3x + 2 -> 5x  or  5."""
    ts, out = list(sp.Add.make_args(sp.expand(expr))), []
    for i in range(len(ts)):
        for j in range(i + 1, len(ts)):
            (ci, mi), (cj, mj) = ts[i].as_coeff_Mul(), ts[j].as_coeff_Mul()
            if mi != mj:
                rest = sum((t for k, t in enumerate(ts) if k not in (i, j)), sp.Integer(0))
                out += [(ci + cj) * mi + rest, (ci + cj) * mj + rest]
    return out


def _dropped(p, c) -> bool:
    return any(t.free_symbols and _same(sp.expand(p) - t, c) for t in sp.Add.make_args(sp.expand(p)))


def _lev1(a: str, b: str) -> bool:
    if a == b:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) == 1
    if abs(len(a) - len(b)) != 1:
        return False
    s, l = sorted((a, b), key=len)
    return any(l[:k] + l[k + 1:] == s for k in range(len(l)))


def _copy_error(P: Rel, C: Rel) -> bool:
    """Same line, but exactly one number lost/changed one digit."""
    tok = lambda r: re.findall(r"\d+\.?\d*|[A-Za-z]|<=|>=|[^\s\w]", r.text)  # noqa: E731
    a, b = tok(P), tok(C)
    if len(a) != len(b):
        return False
    diff = [(x, y) for x, y in zip(a, b) if x != y]
    return len(diff) == 1 and diff[0][0][0].isdigit() and diff[0][1][0].isdigit() and _lev1(*diff[0])


def _structural(P: Rel, C: Rel):
    """Exactly one part changed, and it changed in a recognisable wrong way."""
    changed = [i for i in range(len(P.parts)) if not _same(P.parts[i], C.parts[i])]
    if len(changed) != 1:
        return None
    i = changed[0]
    if _copy_error(P, C):
        return Mistake("copy_error", "certain", HINTS["copy_error"])
    if any(_same(v, C.parts[i]) for v in _dist_variants(P.raw[i])):
        return Mistake("distribution", "certain", HINTS["distribution"])
    if any(_same(v, C.parts[i]) for v in _unlike_variants(P.parts[i])):
        return Mistake("unlike_terms", "certain", HINTS["unlike_terms"])
    if _dropped(P.parts[i], C.parts[i]):
        return Mistake("dropped_term", "certain", HINTS["dropped_term"])
    r = P.raw[i]  # "9 - 3" written as 7: a number expression evaluated wrongly
    if not r.free_symbols and not r.is_Number and C.parts[i].is_Number:
        return Mistake("arithmetic_slip", "certain", HINTS["arithmetic_slip"])
    return None


def _judge(p, c, kind, v):
    """The anchor part moved by (kind, v). What did the student do to this other part?"""
    if _same(c, p + v if kind == "add" else p * v):
        return None
    if _same(c, p):
        return "both_sides"
    if kind == "add":
        if _same(c, p - v):
            return "sign_slip"
        if _same(c, p * v) or (v != 0 and _same(c, p / v)):
            return "wrong_operation"
    else:
        inv = 1 / v
        if _same(c, p / v) or any(_same(c, p + s * k) for s in (1, -1) for k in (v, inv)):
            return "wrong_operation"
    expected = p + v if kind == "add" else p * v
    return "arithmetic_slip" if _num(sp.expand(c - expected)) else "wrong_operation"


def _anchor(P: Rel, C: Rel):
    """Find the part with a clean move (+k or xk) and check every other part against it."""
    anchor = None
    for i, (p, c) in enumerate(zip(P.parts, C.parts)):
        if _same(p, c) or not p.free_symbols:
            continue
        d = sp.expand(c - p)
        if _num(d):
            anchor = (i, "add", d)
            break
        r = sp.simplify(c / p) if p != 0 else None
        if r is not None and _num(r):
            anchor = (i, "mul", r)
            break
    if not anchor:
        return None
    i, kind, v = anchor
    others = [j for j in range(len(P.parts)) if j != i]
    if (kind == "add" and P.parts[i].as_coeff_Add()[0] != 0 and C.parts[i].as_coeff_Add()[0] != 0
            and all(_same(P.parts[j], C.parts[j]) for j in others)):
        return Mistake("arithmetic_slip", "certain", HINTS["arithmetic_slip"])  # e.g. 5x+8 written 5x+7
    for j in others:
        t = _judge(P.parts[j], C.parts[j], kind, v)
        if t is None:
            continue
        side = ("right side" if j == 1 else "left side") if len(P.parts) == 2 else f"part {j + 1}"
        move = _desc(kind, v)
        hints = {
            "sign_slip": f"Try {move} {'to' if kind == 'add' and v > 0 else 'from'} both sides to keep the balance.",
            "both_sides": f"One part got {move} but the {side} didn't. Do the same move on every part.",
            "wrong_operation": f"The two sides got different moves. Try {move} on both sides.",
            "arithmetic_slip": HINTS["arithmetic_slip"],
        }
        return Mistake(t, "certain", hints[t], _practice(P, kind, v) if t != "arithmetic_slip" else None)
    return None


def _generic():
    return Mistake("check", "likely", HINTS["check"])


def diagnose(P: Rel, C: Rel):
    if len(P.parts) != len(C.parts):
        return None  # different shapes: we do not guess
    if len(P.parts) == 1:
        return None if _same(P.parts[0], C.parts[0]) else (_structural(P, C) or _generic())
    com = _common_op(P, C)
    if com:
        return _inequality(P, C, com)
    if _solutions_match(P, C):
        return None
    return _structural(P, C) or _anchor(P, C) or _generic()


# ----------------------------------------------------------------------------- numeric lines
def _ltr(text: str):
    """Evaluate strictly left to right (what students do when they ignore precedence)."""
    toks = re.findall(r"\d+\.?\d*|[-+*/]", _norm(text).replace(" ", ""))
    try:
        i = 2 if toks[0] == "-" else 1
        val = -sp.Rational(toks[1]) if toks[0] == "-" else sp.Rational(toks[0])
        while i < len(toks):
            op, n = toks[i], sp.Rational(toks[i + 1])
            val = val + n if op == "+" else val - n if op == "-" else val * n if op == "*" else val / n
            i += 2
        return val
    except Exception:
        return None


def _numeric_mistake(R: Rel):
    v = R.parts
    if len(v) < 2 or any(e.free_symbols for e in v) or any(o != "=" for o in R.ops):
        return None
    if all(_same(v[0], e) for e in v[1:]):
        return None
    if len(v) >= 3 and re.match(rf"^{re.escape(str(v[0]))}\s*[-+*/]", R.texts[1]):
        return Mistake("equals_sign", "likely", HINTS["equals_sign"])
    k = next(k for k in range(len(v) - 1) if not _same(v[k], v[k + 1]))
    b = v[k + 1]
    if _ltr(R.texts[k]) is not None and _same(_ltr(R.texts[k]), b):
        return Mistake("order_of_ops", "certain", HINTS["order_of_ops"])
    if any(_same(v[k] - 2 * t, b) for t in sp.Add.make_args(R.raw[k]) if len(sp.Add.make_args(R.raw[k])) > 1):
        return Mistake("sign_slip", "certain", HINTS["numeric_sign"])
    return Mistake("arithmetic_slip", "certain", HINTS["arithmetic_slip"])


# ----------------------------------------------------------------------------- whole solution
def _has_paren(raw) -> bool:
    return any(f.is_Add for t in sp.Add.make_args(raw) if t.is_Mul for f in t.args)


def _skipped(P: Rel, C: Rel) -> bool:
    """Brackets removed AND numbers collected in one jump (two moves at once)."""
    if not any(_has_paren(r) for r in P.raw) or any(_has_paren(r) for r in C.raw):
        return False
    for r in P.raw:
        n = 0
        for t in sp.Add.make_args(r):
            if t.is_number:
                n += 1
            elif t.is_Mul:
                n += sum(1 for f in t.args if f.is_Add for u in sp.Add.make_args(f) if u.is_number)
        if n >= 2:
            return True
    return False


def _units(text: str) -> bool:
    fam: dict[str, set] = {}
    for m in _UNIT.finditer(text):
        fam.setdefault(_FAMILY[m.group(1)], set()).add(m.group(1))
    return any(len(u) > 1 for u in fam.values())


def _answer_ok(first: Rel | None, last: Rel | None):
    """Does the final 'x = number' satisfy the very first equation?  None = cannot tell."""
    if not first or not last or last.ops != ["="] or first.ops != ["="]:
        return None
    a, b = last.parts
    pair = (a, b) if a.is_Symbol and _num(b) else (b, a) if b.is_Symbol and _num(a) else None
    if not pair or pair[0] not in first.parts[0].free_symbols | first.parts[1].free_symbols:
        return None
    return _same(first.parts[0].subs(*pair), first.parts[1].subs(*pair))


def check_lines(items: list[LineIn], task_text: str | None = None) -> dict:
    steps, task, prev, first, prev_mixed = [], None, None, None, False
    for n, it in enumerate(items):
        text = it.text.strip()
        if not text:
            continue
        m = _TASK.match(text) if n == 0 else None
        if m:  # "Solve: ..." is the task, not a step
            task = text
            prev = first = parse_line(text[m.end():]) if text[m.end():] else None
            continue
        st = Step(len(steps) + 1, text, "ok", it.box, None, it.unclear)
        steps.append(st)
        mixed = _units(text)
        C = None if (mixed or prev_mixed) else parse_line(text)
        if mixed or prev_mixed:  # unit lines are not parsed as algebra
            if (prev_mixed and not mixed) or (mixed and st.index > 1):
                st.mistake = Mistake("unit_mistake", "likely", HINTS["unit_mistake"])
            prev_mixed, prev = mixed, None
        elif C is None:
            st.status = "unchecked"
            prev = None
        else:
            first = first or C
            if it.unclear:
                st.status = "unreadable"  # ask the student to confirm characters first
            elif not any(e.free_symbols for e in C.parts):
                st.mistake = _numeric_mistake(C)
            elif prev:
                st.mistake = diagnose(prev, C)
                if st.mistake and _skipped(prev, C):
                    st.mistake.also.append("skipped_step")
            prev = C
        if st.status == "ok" and st.mistake:
            st.status = "check"

    for a, b in zip(steps, steps[1:]):  # messy layout: lines drift sideways
        if a.box and b.box and abs(a.box[0] - b.box[0]) > 0.3 and b.status == "ok":
            b.mistake, b.status = Mistake("messy_layout", "likely", HINTS["messy_layout"]), "check"

    mismatch = False
    if task_text and steps:  # compare the student's first line with the photographed task
        tr = parse_line(_TASK.sub("", task_text, count=1))
        if tr and first and len(tr.parts) == len(first.parts) and tr.ops == first.ops:
            mismatch = not all(_same(a, b) for a, b in zip(tr.parts, first.parts))
        if mismatch and steps[0].status == "ok":
            steps[0].mistake = Mistake("copy_error", "likely", "Your first line doesn't match the task. Compare them.")
            steps[0].status = "check"

    last = parse_line(steps[-1].text) if steps else None
    ans = _answer_ok(first, last) if not any(s.unclear for s in steps) else None
    flagged = any(s.status == "check" for s in steps)
    unresolved = any(s.mistake and s.mistake.type == "check" for s in steps)
    need = unresolved or (not flagged and (ans is False or any(s.status == "unchecked" for s in steps)))
    return {"task": task, "steps": [s.to_dict() for s in steps], "needs_task_photo": bool(need) and not task_text,
            "answer_ok": ans, "task_mismatch": mismatch}
