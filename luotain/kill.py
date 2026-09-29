"""Kill matrices, the published map, and equivalence classes.

kill(SA, SB)[i, j] is True when some probe obeys law A_i and breaks law B_j, which
certifies that A_i does NOT imply B_j.  It is one matrix product.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

DATA = Path(__file__).resolve().parent.parent / "data" / "etp"

# codes in the ETP outcome matrix (2024-11-10 snapshot)
TRUE_CODES = ("implicit_proof_true", "explicit_proof_true")
FALSE_CODES = ("implicit_proof_false", "explicit_proof_false",
               "implicit_conjecture_false", "explicit_conjecture_false")


def kill(SA: np.ndarray, SB: np.ndarray, chunk: int = 2048) -> np.ndarray:
    """(len(SA), len(SB)) bool: some probe obeys A_i and breaks B_j."""
    A = SA.astype(np.float32)
    notB = (~SB).astype(np.float32).T.copy()
    out = np.zeros((len(SA), len(SB)), dtype=bool)
    for s in range(0, len(SA), chunk):
        out[s:s + chunk] = (A[s:s + chunk] @ notB) > 0.5
    return out


def published_map():
    """The ETP outcome matrix for Equations 1..4694.

    Returns (truth, code, names) where truth[i, j] is True/False for 'E(i+1) implies
    E(j+1)', code holds the raw outcome codes and names maps codes to strings.
    The 2024-11-10 snapshot still lists 4 pairs as unknown and 186 as conjectured
    false; the project's final count (8,178,279 true pairs, diagonal included) equals
    this snapshot's true count, so all 190 were settled as false afterwards."""
    M = np.load(DATA / "outcomes_2024-11-10.npz")["outcomes"]
    names = {int(k): v for k, v in json.loads((DATA / "outcomes_meta.json").read_text())["codes"].items()}
    true_ids = [k for k, v in names.items() if v in TRUE_CODES]
    truth = np.isin(M, true_ids)
    return truth, M, names


def classes(truth: np.ndarray) -> np.ndarray:
    """Equivalence class id per law (mutual implication), numbered by first member."""
    eq = truth & truth.T
    cls = -np.ones(len(truth), dtype=np.int64)
    k = 0
    for i in range(len(truth)):
        if cls[i] < 0:
            cls[eq[i]] = k
            k += 1
    return cls


def hasse(truth: np.ndarray, cls: np.ndarray) -> list[tuple[int, int]]:
    """Cover relations between classes (the transitive reduction), as (stronger, weaker)."""
    k = cls.max() + 1
    rep = np.array([np.flatnonzero(cls == c)[0] for c in range(k)])
    C = truth[np.ix_(rep, rep)].copy()
    np.fill_diagonal(C, False)
    Ci = C.astype(np.int32)
    two_step = (Ci @ Ci) > 0
    cover = C & ~two_step
    return [(int(a), int(b)) for a, b in zip(*np.nonzero(cover))]
