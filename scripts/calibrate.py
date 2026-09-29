"""Step 1: calibrate the probes on the published map.

The Equational Theories Project settled all 22,028,942 implications between the
4,694 laws with at most four operations.  About 13.86 million are false.  How many
of those can small multiplication tables kill on their own?  And do the probes ever
"kill" a true implication?  (They must not: that would mean a bug.)

    python scripts/fingerprints.py --upto 4694     # or the full run
    python scripts/calibrate.py

Writes results/calibration.json and results/calibration_residue.npz.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from luotain.kill import classes, kill, published_map
from luotain.laws import load
from luotain.probes import ProbeSet, random_tables, respond_all
from scripts.fingerprints import load_responses

N_OLD = 4694


def main():
    t0 = time.time()
    laws = load()[:N_OLD]
    truth, code, names = published_map()
    off = ~np.eye(N_OLD, dtype=bool)
    true_e = truth & off
    false_e = ~truth & off
    unknown_code = [k for k, v in names.items() if v == "unknown"]
    conj_codes = [k for k, v in names.items() if "conjecture" in v]
    print(f"published map: {true_e.sum():,} true, {false_e.sum():,} false (off-diagonal)")

    families = []
    for k in range(3):
        S, name = load_responses(k)
        families.append((name, S[:N_OLD]))
    rnd = ProbeSet("2,000 random 4-element tables", tables=random_tables(4, 2000, seed=0))
    t = time.time()
    families.append((rnd.name, respond_all(laws, rnd)))
    print(f"random 4-element tables: {time.time() - t:.0f}s")

    killed = np.zeros_like(false_e)
    rows = []
    for name, S in families:
        K = kill(S, S)
        bad = int((K & true_e).sum())
        new = K & ~killed & false_e
        killed |= K
        rows.append({
            "family": name,
            "probes": int(S.shape[1]),
            "distinct_responses": int(len(np.unique(np.packbits(S, axis=0), axis=1)[0])),
            "kills_alone": int((K & false_e).sum()),
            "new_kills": int(new.sum()),
            "cumulative_kills": int((killed & false_e).sum()),
            "kills_on_true_edges": bad,
        })
        print(f"{name:45s} alone {rows[-1]['kills_alone']:>11,}  new {rows[-1]['new_kills']:>11,}  "
              f"cumulative {rows[-1]['cumulative_kills']:>11,}  on-true {bad}", flush=True)
        assert bad == 0, f"{name} killed {bad} TRUE implications: evaluator bug"

    residue = false_e & ~killed
    cls = classes(truth)
    k = cls.max() + 1
    rep = np.array([np.flatnonzero(cls == c)[0] for c in range(k)])
    res_cls = residue[np.ix_(rep, rep)]
    false_cls = false_e[np.ix_(rep, rep)] & ~np.eye(k, dtype=bool)
    pairs = np.argwhere(residue)
    res_codes = {names[c]: int(n) for c, n in zip(*np.unique(code[residue], return_counts=True))}
    summary = {
        "source": "ETP outcome matrix, snapshot 2024-11-10 (4 unknown + 186 conjectured pairs, all later settled false)",
        "laws": N_OLD,
        "classes": int(k),
        "true_edges": int(true_e.sum()),
        "false_edges": int(false_e.sum()),
        "families": rows,
        "killed": int((killed & false_e).sum()),
        "killed_fraction": float((killed & false_e).sum() / false_e.sum()),
        "residue_edges": int(residue.sum()),
        "residue_by_published_code": res_codes,
        "class_level": {"false_class_pairs": int(false_cls.sum()), "residue_class_pairs": int(res_cls.sum())},
        "unknown_in_snapshot_killed": int((killed & np.isin(code, unknown_code)).sum()),
        "conjectured_in_snapshot_killed": int((killed & np.isin(code, conj_codes)).sum()),
        "seconds": round(time.time() - t0),
    }
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "calibration.json").write_text(json.dumps(summary, indent=1))
    np.savez_compressed(ROOT / "results" / "calibration_residue.npz", pairs=(pairs + 1).astype(np.int16),
                        note="1-based ETP equation numbers (A, B): A does not imply B, and no probe here shows it")
    print(json.dumps({k: v for k, v in summary.items() if k != "families"}, indent=1))


if __name__ == "__main__":
    main()
