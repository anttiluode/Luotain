"""Checks against the Equational Theories Project's published map."""
import numpy as np

from luotain.kill import classes, hasse, kill, published_map
from luotain.laws import load
from luotain.probes import all_tables, iso_reps, respond_all, ProbeSet

LAWS = load()
TRUTH, CODE, NAMES = published_map()


def test_published_counts():
    off = ~np.eye(4694, dtype=bool)
    assert (TRUTH & off).sum() == 8_173_585            # true implications between distinct laws
    assert (~TRUTH & off).sum() == 13_855_357          # false ones (incl. 190 settled after the snapshot)
    assert classes(TRUTH).max() + 1 == 1415


def test_cover_edges_match_published_count():
    # Berlioz & Melliès report the class graph as 1415 vertices and 4824 edges
    assert len(hasse(TRUTH, classes(TRUTH))) == 4824


def test_probes_never_kill_a_true_implication():
    rng = np.random.default_rng(0)
    idx = np.sort(rng.choice(4694, 400, replace=False))
    probes = ProbeSet("t3", tables=iso_reps(all_tables(3)))
    S = respond_all([LAWS[i] for i in idx], probes)
    K = kill(S, S)
    T = TRUTH[np.ix_(idx, idx)]
    assert not (K & T).any()
    assert (K & ~T).sum() > 0.9 * (~T).sum()          # and they kill most false ones (96% on the full map)


def test_kill_is_existential():
    SA = np.array([[1, 0, 0], [0, 0, 0]], dtype=bool)
    SB = np.array([[1, 1, 0], [0, 1, 1]], dtype=bool)
    # law A0 obeyed by probe 0; B1 breaks probe 0 -> A0 does not imply B1
    assert kill(SA, SB).tolist() == [[False, True], [False, False]]
