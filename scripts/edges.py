"""Step 3: full edges for a sample of genuinely new laws.

For a sample of the five-multiplication laws that no old law resembles (one per
fingerprint group), decide every edge to and from the 1,415 old classes:

    L -> c   killed if some probe obeys L and breaks c; otherwise asked of Vampire.
    c -> L   the same, the other way round.

Answers propagate along the old map, so few questions are asked:
    L -> c proved     =>  L -> every class c implies
    L -> c refuted    =>  L -/-> every class that implies c
    c -> L proved     =>  every class that implies c also implies L
    c -> L refuted    =>  no class implied by c implies L

Whatever stays open is the residue: edges neither the probes nor Vampire settled.

    python scripts/edges.py --sample 120
"""
import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from luotain.kill import kill
from luotain.laws import load
from luotain.prove import PROVED, REFUTED, vampire
from scripts.place import N_OLD, setup

OUT = ROOT / "results" / "sample_edges.jsonl"

YES, NO, OPEN = 1, 0, -1


def place_one(i, laws, S, rep_ids, C, seconds):
    """Edges between new law i and every old class (rows of C are 'implies')."""
    k = len(rep_ids)
    L = laws[i]
    SL = S[i:i + 1]
    SR = S[rep_ids]
    up_kill = kill(SL, SR)[0]            # probe obeys L, breaks c   => L -/-> c
    down_kill = kill(SR, SL)[:, 0]       # probe obeys c, breaks L   => c -/-> L
    up = np.full(k, OPEN)
    down = np.full(k, OPEN)
    up[up_kill] = NO
    down[down_kill] = NO
    stats = {"probe_kills_up": int(up_kill.sum()), "probe_kills_down": int(down_kill.sum()),
             "vampire_calls": 0, "vampire_proved": 0, "vampire_refuted": 0, "vampire_unknown": 0}
    strength = C.sum(axis=1)             # how many classes each class implies

    # L -> c : strongest candidates first; a proof settles everything weaker at once
    for c in np.argsort(-strength, kind="stable"):
        if up[c] != OPEN:
            continue
        v, _ = vampire(L, laws[rep_ids[c]], seconds)
        stats["vampire_calls"] += 1
        if v == PROVED:
            stats["vampire_proved"] += 1
            up[C[c] & (up == OPEN)] = YES
            up[c] = YES
        elif v == REFUTED:
            stats["vampire_refuted"] += 1
            up[C[:, c] & (up == OPEN)] = NO
            up[c] = NO
        else:
            stats["vampire_unknown"] += 1
    # c -> L : weakest candidates first; a proof settles everything stronger at once
    for c in np.argsort(strength, kind="stable"):
        if down[c] != OPEN:
            continue
        v, _ = vampire(laws[rep_ids[c]], L, seconds)
        stats["vampire_calls"] += 1
        if v == PROVED:
            stats["vampire_proved"] += 1
            down[C[:, c] & (down == OPEN)] = YES
            down[c] = YES
        elif v == REFUTED:
            stats["vampire_refuted"] += 1
            down[C[c] & (down == OPEN)] = NO
            down[c] = NO
        else:
            stats["vampire_unknown"] += 1
    # the strongest classes L implies (its parents on the map) and the weakest that imply it
    implied = np.flatnonzero(up == YES)
    parents = [int(c) for c in implied if not any(C[c2, c] and c2 != c for c2 in implied)]
    implying = np.flatnonzero(down == YES)
    children = [int(c) for c in implying if not any(C[c, c2] and c2 != c for c2 in implying)]
    assert not ((up == YES) & (down == YES)).any(), f"E{i + 1} equivalent to an old class?"
    return {"id": i + 1, "law": L.text,
            "implies": int((up == YES).sum()), "not_implies": int((up == NO).sum()),
            "open_up": [int(rep_ids[c]) + 1 for c in np.flatnonzero(up == OPEN)],
            "implied_by": int((down == YES).sum()), "not_implied_by": int((down == NO).sum()),
            "open_down": [int(rep_ids[c]) + 1 for c in np.flatnonzero(down == OPEN)],
            "parents": [int(rep_ids[c]) + 1 for c in parents],
            "children": [int(rep_ids[c]) + 1 for c in children],
            **stats}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=120)
    ap.add_argument("--seconds", type=float, default=2.0)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    laws, S, truth, cls, rep, keys, zero, old_by_key = setup()
    classes_sorted = sorted(rep)
    rep_ids = np.array([rep[c] for c in classes_sorted])
    C = truth[np.ix_(rep_ids, rep_ids)]
    groups = {}
    for i in range(N_OLD, len(laws)):
        if not zero[i] and keys[i] not in old_by_key:
            groups.setdefault(keys[i], i)
    reps = sorted(groups.values())
    rng = np.random.default_rng(a.seed)
    pick = sorted(rng.choice(reps, size=min(a.sample, len(reps)), replace=False).tolist())
    done = set()
    if OUT.exists():
        done = {json.loads(l)["id"] for l in OUT.read_text().splitlines() if l.strip()}
    todo = [i for i in pick if i + 1 not in done]
    print(f"{len(reps)} new fingerprint groups; sample {len(pick)}; {len(todo)} to do", flush=True)
    t0 = time.time()
    with open(OUT, "a") as f, ThreadPoolExecutor(max_workers=2) as ex:
        for k, rec in enumerate(ex.map(lambda i: place_one(i, laws, S, rep_ids, C, a.seconds), todo)):
            f.write(json.dumps(rec) + "\n")
            f.flush()
            print(f"  E{rec['id']}: implies {rec['implies']}, implied by {rec['implied_by']}, "
                  f"open {len(rec['open_up'])}+{len(rec['open_down'])}, vampire calls {rec['vampire_calls']}  "
                  f"[{k + 1}/{len(todo)}, {time.time() - t0:.0f}s]", flush=True)


if __name__ == "__main__":
    main()
