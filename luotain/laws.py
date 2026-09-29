"""Laws of one binary operation, in the Equational Theories Project's notation.

A term is either a variable (an int, numbered by first appearance) or a pair
(left, right) meaning ``left ◇ right``.  A law is ``lhs = rhs``, read as holding
for every choice of the variables.

The ETP numbers every law of order <= 5 in ``data/etp/eq_size5.txt``: line k is
Equation k.  Equations 1..4694 have at most four operations; 4695..62576 have
exactly five.  We keep their numbering everywhere so results line up with theirs.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

OP = "◇"
NAMES = ["x", "y", "z", "w", "u", "v", "r", "s", "t"]   # the ETP's variable letters, in order
DATA = Path(__file__).resolve().parent.parent / "data" / "etp"

Term = "int | tuple"


# ----------------------------------------------------------------------------- parsing

_TOKEN = re.compile(r"\s*([a-z]+|\(|\)|◇|=)")


def _tokens(s: str) -> list[str]:
    out, pos = [], 0
    s = s.strip()
    while pos < len(s):
        m = _TOKEN.match(s, pos)
        if not m:
            raise ValueError(f"cannot parse {s!r} at {pos}")
        out.append(m.group(1))
        pos = m.end()
    return out


def parse(text: str) -> tuple:
    """'x ◇ (y ◇ x) = y' -> (lhs, rhs, nvars).  Variables are renumbered by first appearance."""
    toks = _tokens(text)
    names: dict[str, int] = {}
    pos = 0

    def atom():
        nonlocal pos
        t = toks[pos]
        if t == "(":
            pos += 1
            e = expr()
            assert toks[pos] == ")", text
            pos += 1
            return e
        pos += 1
        if t not in names:
            names[t] = len(names)
        return names[t]

    def expr():
        nonlocal pos
        left = atom()
        while pos < len(toks) and toks[pos] == OP:
            pos += 1
            left = (left, atom())
        return left

    lhs = expr()
    assert toks[pos] == "=", text
    pos += 1
    rhs = expr()
    assert pos == len(toks), text
    return lhs, rhs, len(names)


def show(t, top: bool = True) -> str:
    if isinstance(t, int):
        return NAMES[t]
    s = f"{show(t[0], False)} {OP} {show(t[1], False)}"
    return s if top else f"({s})"


def order(t) -> int:
    return 0 if isinstance(t, int) else 1 + order(t[0]) + order(t[1])


def variables(t, acc=None) -> list[int]:
    acc = [] if acc is None else acc
    if isinstance(t, int):
        if t not in acc:
            acc.append(t)
    else:
        variables(t[0], acc)
        variables(t[1], acc)
    return acc


def dual(t):
    """Mirror every product: a ◇ b -> b ◇ a.  A magma obeys a law iff its transpose obeys the dual."""
    return t if isinstance(t, int) else (dual(t[1]), dual(t[0]))


@dataclass(frozen=True)
class Law:
    id: int          # ETP equation number (1-based)
    lhs: object
    rhs: object
    nvars: int

    @property
    def order(self) -> int:
        return order(self.lhs) + order(self.rhs)

    @property
    def text(self) -> str:
        return f"{show(self.lhs)} = {show(self.rhs)}"

    def __str__(self) -> str:
        return f"E{self.id}: {self.text}"


def load(path: Path | None = None) -> list[Law]:
    """All 62,576 ETP laws of order <= 5, as Law objects; index i holds Equation i+1."""
    path = path or DATA / "eq_size5.txt"
    laws = []
    for k, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        lhs, rhs, n = parse(line)
        laws.append(Law(k, lhs, rhs, n))
    return laws


# ----------------------------------------------------------------------------- emitters

def tptp_term(t) -> str:
    return f"X{t}" if isinstance(t, int) else f"m({tptp_term(t[0])},{tptp_term(t[1])})"


def tptp_law(law: Law) -> str:
    vs = ",".join(f"X{i}" for i in range(law.nvars))
    body = f"{tptp_term(law.lhs)} = {tptp_term(law.rhs)}"
    return f"![{vs}]: ({body})" if law.nvars else body


def tptp_problem(hyp: Law, goal: Law) -> str:
    return (f"fof(hyp, axiom, {tptp_law(hyp)}).\n"
            f"fof(goal, conjecture, {tptp_law(goal)}).\n")


def _lean(t, op: str) -> str:
    if isinstance(t, int):
        return NAMES[t]
    a, b = (_lean(s, op) for s in t)
    a = a if isinstance(t[0], int) else f"({a})"
    b = b if isinstance(t[1], int) else f"({b})"
    return f"{op} {a} {b}"


def lean_prop(law: Law, op: str = "op", ty: str = "α") -> str:
    """'∀ x y : α, op x (op y x) = y' — the law as a Lean proposition about `op`."""
    body = f"{_lean(law.lhs, op)} = {_lean(law.rhs, op)}"
    if law.nvars == 0:
        return body
    vs = " ".join(NAMES[i] for i in range(law.nvars))
    return f"∀ {vs} : {ty}, {body}"
