"""The parser round-trips the ETP's own list, and the counts match their formula."""
from collections import Counter

from luotain.laws import DATA, dual, lean_prop, load, parse, show, tptp_problem

LAWS = load()


def test_round_trip_every_line():
    lines = (DATA / "eq_size5.txt").read_text(encoding="utf-8").splitlines()
    assert len(lines) == len(LAWS) == 62576
    assert all(law.text == line for law, line in zip(LAWS, lines))


def test_counts_by_order():
    # 2, 5, 39, 364, 4284, 57882 (OEIS A376640)
    assert sorted(Counter(l.order for l in LAWS).items()) == [(0, 2), (1, 5), (2, 39), (3, 364), (4, 4284), (5, 57882)]


def test_known_numbers():
    assert LAWS[1].text == "x = y"                   # Equation 2, the law with only one-element models
    assert LAWS[4].text == "x = y ◇ x"               # Equation 5
    assert LAWS[4693].text == "(x ◇ y) ◇ z = (w ◇ u) ◇ v"


def test_dual_and_emitters():
    lhs, rhs, n = parse("x ◇ (y ◇ z) = y")
    assert show(dual(lhs)) == "(z ◇ y) ◇ x"
    assert "∀ x y : α, x = op y x" == lean_prop(LAWS[4])
    assert "fof(goal, conjecture, ![X0,X1]: (X0 = m(X1,X0)))" in tptp_problem(LAWS[2], LAWS[4])
