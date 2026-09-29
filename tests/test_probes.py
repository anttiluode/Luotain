"""The evaluator has to be right before any count means anything.  These tests check
it against a slow, obviously-correct evaluator, and check the affine shortcut against
the tables it stands for."""
import itertools
import random

import numpy as np
import pytest

from luotain.laws import load, parse, Law
from luotain.probes import (Affine, all_tables, iso_reps, random_tables, respond_affine,
                            respond_tables)

LAWS = load()


def naive_obeys(law: Law, T) -> bool:
    n = len(T)

    def ev(t, env):
        return env[t] if isinstance(t, int) else int(T[ev(t[0], env)][ev(t[1], env)])

    return all(ev(law.lhs, env) == ev(law.rhs, env)
               for env in itertools.product(range(n), repeat=law.nvars))


def test_iso_class_counts():
    # magmas up to isomorphism: 1, 10, 3330 (OEIS A001329)
    assert len(iso_reps(all_tables(2))) == 10
    assert len(iso_reps(all_tables(3))) == 3330


@pytest.mark.parametrize("n,seed", [(2, 0), (3, 1), (4, 2)])
def test_tables_match_naive(n, seed):
    rng = random.Random(seed)
    T = random_tables(n, 40, seed=seed)
    for law in rng.sample(LAWS, 60) + LAWS[:8]:
        fast = respond_tables(law, T)
        slow = [naive_obeys(law, t.tolist()) for t in T]
        assert fast.tolist() == slow, law


def test_affine_matches_its_tables():
    rng = random.Random(3)
    A = Affine.grid([2, 3, 4, 5])
    pick = rng.sample(range(len(A)), 60)
    for law in rng.sample(LAWS, 60):
        sym = respond_affine(law, A)
        for i in pick:
            assert sym[i] == naive_obeys(law, A.table(i).tolist()), (law, i)


def test_known_facts():
    # associativity holds in (Z/2, +), left projection x◇y = x does not
    lhs, rhs, n = parse("x ◇ (y ◇ z) = (x ◇ y) ◇ z")
    assoc = Law(0, lhs, rhs, n)
    lhs, rhs, n = parse("x = x ◇ y")
    proj = Law(0, lhs, rhs, n)
    add = np.array([[[0, 1], [1, 0]]], dtype=np.uint8)
    assert respond_tables(assoc, add)[0] and not respond_tables(proj, add)[0]
    left = np.array([[[0, 0], [1, 1]]], dtype=np.uint8)   # x◇y = x
    assert respond_tables(proj, left)[0]


def test_stone_pairing_of_x_equals_y():
    lhs, rhs, n = parse("x = y")
    law = Law(2, lhs, rhs, n)
    T = random_tables(3, 5)
    assert np.allclose(respond_tables(law, T, stone=True), 1 / 3)
