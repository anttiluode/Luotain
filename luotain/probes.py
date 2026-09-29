"""Probes: small multiplication tables, and which laws each one obeys.

A probe is a finite magma.  Its response to a law is whether the law holds for
every choice of the variables (``obeys``), or the fraction of choices for which it
holds (the Stone pairing, used only for drawing the map).

If law A implies law B, every probe that obeys A obeys B.  So one probe that obeys
A and breaks B is a certificate that A does not imply B.  That is the whole trick.

Families:
    tables(n)       every n-element table, one per isomorphism class (n = 2, 3)
    affine(...)     x◇y = a·x + b·y + c over Z/n, evaluated symbolically, so large n is cheap
    random(n, k)    k random n-element tables (seeded)
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field

import numpy as np

from .laws import Law


# ----------------------------------------------------------------------------- tables

def all_tables(n: int) -> np.ndarray:
    """Every n x n table with entries in 0..n-1, shape (n**(n*n), n, n)."""
    cells = n * n
    idx = np.arange(n ** cells, dtype=np.int64)
    out = np.empty((len(idx), cells), dtype=np.uint8)
    for c in range(cells - 1, -1, -1):
        out[:, c] = idx % n
        idx //= n
    return out.reshape(-1, n, n)


def iso_reps(T: np.ndarray) -> np.ndarray:
    """One table per isomorphism class (relabelling the elements).  Laws cannot tell
    isomorphic tables apart, so this loses nothing."""
    P, n, _ = T.shape
    flat = T.reshape(P, -1).astype(np.int64)
    weights = n ** np.arange(n * n - 1, -1, -1, dtype=np.int64)
    best = None
    for perm in itertools.permutations(range(n)):
        p = np.array(perm)
        inv = np.argsort(p)
        # relabelled table: T'[p[i], p[j]] = p[T[i, j]]  <=>  T'[i, j] = p[T[inv[i], inv[j]]]
        R = p[T[:, inv][:, :, inv]].reshape(P, -1).astype(np.int64)
        code = R @ weights
        best = code if best is None else np.minimum(best, code)
    _, first = np.unique(best, return_index=True)
    return T[np.sort(first)]


def random_tables(n: int, k: int, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(0, n, size=(k, n, n), dtype=np.uint8)


# ----------------------------------------------------------------------------- evaluation on tables

def _eval(term, Tf: np.ndarray, n: int, assign: list[np.ndarray]):
    """Value of `term` for every table (rows of Tf) and every assignment (columns).
    Returns an (A,) array when no product is involved, else (P, A)."""
    if isinstance(term, int):
        return assign[term]
    a = _eval(term[0], Tf, n, assign)
    b = _eval(term[1], Tf, n, assign)
    idx = a.astype(np.intp) * n + b
    if idx.ndim == 1:
        return Tf[:, idx]
    return np.take_along_axis(Tf, idx, axis=1)


def _assignments(n: int, k: int) -> list[np.ndarray]:
    if k == 0:
        return []
    grid = np.indices((n,) * k, dtype=np.uint8).reshape(k, -1)
    return [grid[j] for j in range(k)]


def respond_tables(law: Law, T: np.ndarray, stone: bool = False) -> np.ndarray:
    """(P,) bool: does each table obey the law?  With stone=True, the fraction of
    variable choices that satisfy it instead."""
    P, n, _ = T.shape
    Tf = T.reshape(P, n * n)
    assign = _assignments(n, law.nvars)
    lhs = _eval(law.lhs, Tf, n, assign)
    rhs = _eval(law.rhs, Tf, n, assign)
    lhs, rhs = np.broadcast_arrays(lhs, rhs)
    if lhs.ndim == 1:                       # x = x style: no products at all
        eq = np.broadcast_to(lhs == rhs, (P, lhs.shape[0]))
    else:
        eq = lhs == rhs
    if stone:
        return eq.mean(axis=1)
    return eq.all(axis=1)


# ----------------------------------------------------------------------------- affine probes, symbolically

@dataclass
class Affine:
    """x◇y = a·x + b·y + c (mod n), one probe per row."""
    n: np.ndarray
    a: np.ndarray
    b: np.ndarray
    c: np.ndarray

    def __len__(self):
        return len(self.n)

    @staticmethod
    def grid(ns) -> "Affine":
        rows = [(n, a, b, c) for n in ns for a in range(n) for b in range(n) for c in range(n)]
        arr = np.array(rows, dtype=np.int64)
        return Affine(arr[:, 0], arr[:, 1], arr[:, 2], arr[:, 3])

    def table(self, i: int) -> np.ndarray:
        n, a, b, c = int(self.n[i]), int(self.a[i]), int(self.b[i]), int(self.c[i])
        x = np.arange(n)
        return ((a * x[:, None] + b * x[None, :] + c) % n).astype(np.uint8)


def _affine_eval(term, P: Affine, k: int):
    """Term -> (coefficients (Q, k), constant (Q,)) with value = sum coef_j x_j + const mod n."""
    if isinstance(term, int):
        co = np.zeros((len(P), k), dtype=np.int64)
        co[:, term] = 1
        return co, np.zeros(len(P), dtype=np.int64)
    ca, ka = _affine_eval(term[0], P, k)
    cb, kb = _affine_eval(term[1], P, k)
    n = P.n
    co = (P.a[:, None] * ca + P.b[:, None] * cb) % n[:, None]
    const = (P.a * ka + P.b * kb + P.c) % n
    return co, const


def respond_affine(law: Law, P: Affine) -> np.ndarray:
    k = max(law.nvars, 1)
    cl, kl = _affine_eval(law.lhs, P, k)
    cr, kr = _affine_eval(law.rhs, P, k)
    return ((cl % P.n[:, None]) == (cr % P.n[:, None])).all(axis=1) & ((kl % P.n) == (kr % P.n))


# ----------------------------------------------------------------------------- probe sets

@dataclass
class ProbeSet:
    name: str
    tables: np.ndarray | None = None
    affine: Affine | None = None
    labels: list = field(default_factory=list)

    def __len__(self):
        return len(self.tables) if self.tables is not None else len(self.affine)

    def respond(self, law: Law) -> np.ndarray:
        if self.tables is not None:
            return respond_tables(law, self.tables)
        return respond_affine(law, self.affine)

    def table(self, i: int) -> np.ndarray:
        return self.tables[i] if self.tables is not None else self.affine.table(i)


def respond_all(laws: list[Law], probes: ProbeSet, progress: bool = False) -> np.ndarray:
    """(len(laws), len(probes)) bool matrix: law i obeyed by probe j."""
    S = np.zeros((len(laws), len(probes)), dtype=bool)
    for i, law in enumerate(laws):
        S[i] = probes.respond(law)
        if progress and i % 5000 == 0:
            print(f"  {probes.name}: {i}/{len(laws)}", flush=True)
    return S


def standard_families(seed: int = 0) -> list[ProbeSet]:
    """The probe families used throughout, cheapest first."""
    t2 = iso_reps(all_tables(2))
    t3 = iso_reps(all_tables(3))
    aff = Affine.grid(range(2, 13))
    return [
        ProbeSet("all 2-element tables", tables=t2),
        ProbeSet("all 3-element tables", tables=t3),
        ProbeSet("affine x◇y = ax+by+c mod n, n <= 12", affine=aff),
    ]


def dedupe_columns(S: np.ndarray) -> np.ndarray:
    """Indices of probes with distinct response columns (the rest add nothing)."""
    packed = np.packbits(S, axis=0)
    _, first = np.unique(packed, axis=1, return_index=True)
    return np.sort(first)
