"""Step 2: place the 57,882 five-multiplication laws onto the published map.

For each new law L (Equations 4695..62576):

  collapse   no probe obeys L, and Vampire proves L -> (x = y): L only has one-element
             models, so it sits with Equation 2 at the top of the map.
  joins      L's fingerprint equals an old class's, and Vampire proves both directions:
             L is equivalent to a law with at most four operations.
  new        L's fingerprint differs from every old law's.  That alone certifies L is
             inequivalent to all 4,694 old laws (a probe separates it from each).
             Distinct fingerprints among these are distinct classes, so their count is
             a lower bound on how many classes order 5 adds.
  residue    anything the probes and Vampire could not settle within the time limits.

    python scripts/place.py            # resumable; appends to cache/place.jsonl
    python scripts/place.py --retry    # second look at what is left (finite models, longer proofs)
    python scripts/place.py --report   # summarise into results/
"""
import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from luotain.kill import classes, published_map
from luotain.laws import load
from luotain.prove import PROVED, REFUTED, vampire
from scripts.fingerprints import load_responses

N_OLD = 4694
E2 = 1                       # index of Equation 2, x = y
LOG = ROOT / "cache" / "place.jsonl"


def setup():
    laws = load()
    S = np.concatenate([load_responses(k)[0] for k in range(3)], axis=1)
    truth, _, _ = published_map()
    cls = classes(truth)
    P = np.packbits(S, axis=1)
    keys = [P[i].tobytes() for i in range(len(P))]
    zero = ~P.any(axis=1)
    rep = {}
    for i in range(N_OLD):
        rep.setdefault(int(cls[i]), i)                   # lowest-numbered law in each class
    old_by_key = defaultdict(list)
    for c, i in sorted(rep.items()):
        old_by_key[keys[i]].append(c)
    return laws, S, truth, cls, rep, keys, zero, old_by_key


def decide(task, laws, rep, seconds):
    """One new law -> a record."""
    i, kind, cands = task
    L = laws[i]
    if kind == "zero":
        v, _ = vampire(L, laws[E2], seconds)
        return {"id": i + 1, "kind": kind, "status": {"proved": "collapse", "refuted": "not_collapse"}.get(v, "residue")}
    tried = []
    for c in cands:
        a, _ = vampire(L, laws[rep[c]], seconds)
        if a == PROVED:
            b, _ = vampire(laws[rep[c]], L, seconds)
            tried.append((c, a, b))
            if b == PROVED:
                return {"id": i + 1, "kind": kind, "status": "joins", "class": c, "rep": rep[c] + 1}
        else:
            tried.append((c, a, None))
    status = "not_joined" if all(t[1] == REFUTED or t[2] == REFUTED for t in tried) else "residue"
    return {"id": i + 1, "kind": kind, "status": status, "tried": tried}


def run(seconds: float, workers: int):
    laws, S, truth, cls, rep, keys, zero, old_by_key = setup()
    done = set()
    if LOG.exists():
        done = {json.loads(l)["id"] for l in LOG.read_text().splitlines() if l.strip()}
    tasks = []
    for i in range(N_OLD, len(laws)):
        if i + 1 in done:
            continue
        if zero[i]:
            tasks.append((i, "zero", []))
        elif keys[i] in old_by_key:
            tasks.append((i, "match", old_by_key[keys[i]]))
        else:
            continue                                          # certified new by probes alone
    tasks.sort(key=lambda t: (t[1] != "zero", len(t[2])))      # cheapest first
    print(f"{len(tasks)} laws need Vampire ({len(done)} already done)", flush=True)
    t0 = time.time()
    with open(LOG, "a") as f, ThreadPoolExecutor(max_workers=workers) as ex:
        for k, rec in enumerate(ex.map(lambda t: decide(t, laws, rep, seconds), tasks)):
            f.write(json.dumps(rec) + "\n")
            if k % 500 == 0:
                f.flush()
                print(f"  {k}/{len(tasks)}  {time.time() - t0:.0f}s", flush=True)


def decide_retry(task, laws, rep, seconds):
    """Second look at an unsettled law: finite-model search first (a model of one law that
    breaks the other excludes that class quickly), then a longer proof attempt."""
    i, kind, cands = task
    L = laws[i]
    tried = []
    for c in cands:
        R = laws[rep[c]]
        if vampire(R, L, seconds, mode="fmb")[0] == REFUTED:
            tried.append((c, "refuted", None))
            continue
        if vampire(L, R, seconds, mode="fmb")[0] == REFUTED:
            tried.append((c, "refuted", None))
            continue
        a, _ = vampire(L, R, 2 * seconds)
        b = vampire(R, L, 2 * seconds)[0] if a == PROVED else None
        if a == PROVED and b == PROVED:
            return {"id": i + 1, "kind": kind, "status": "joins", "class": c, "rep": rep[c] + 1}
        tried.append((c, a, b))
    status = "not_joined" if all(t[1] == REFUTED or t[2] == REFUTED for t in tried) else "residue"
    return {"id": i + 1, "kind": kind, "status": status, "tried": tried}


def run_retry(seconds: float, workers: int, max_minutes: float = 30.0):
    """Second pass over everything left unsettled by the first, within a time budget."""
    laws, S, truth, cls, rep, keys, zero, old_by_key = setup()
    zero_classes = sorted({int(cls[i]) for i in range(N_OLD) if zero[i]} - {int(cls[E2])})
    recs = {}
    for l in LOG.read_text().splitlines():
        if l.strip():
            r = json.loads(l)
            recs[r["id"]] = r
    tasks = []
    for r in recs.values():
        i = r["id"] - 1
        if r["kind"] == "zero" and r["status"] in ("not_collapse", "residue"):
            tasks.append((i, "zero2", zero_classes))
        elif r["kind"] == "match" and r["status"] == "residue":
            tasks.append((i, "match2", old_by_key[keys[i]]))
    print(f"{len(tasks)} unsettled laws get a second look", flush=True)
    t0 = time.time()

    def one(task):
        if time.time() - t0 > 60 * max_minutes:            # out of budget: leave it as it was
            return None
        return decide_retry(task, laws, rep, seconds)

    with open(LOG, "a") as f, ThreadPoolExecutor(max_workers=workers) as ex:
        for k, rec in enumerate(ex.map(one, tasks)):
            if rec is None:
                continue
            prev = recs[rec["id"]]
            if rec["kind"] == "zero2" and rec["status"] != "joins":
                # new only if it also provably does not collapse
                rec["status"] = "not_joined" if (prev["status"] == "not_collapse" and rec["status"] == "not_joined") else "residue"
            f.write(json.dumps(rec) + "\n")
            if k % 200 == 0:
                f.flush()
                print(f"  {k}/{len(tasks)}  {time.time() - t0:.0f}s", flush=True)


LABELS = {
    "collapse": "Collapse to x = y (Vampire proof; no probe obeys them)",
    "joins": "Equivalent to an older law (Vampire proofs both ways)",
    "new": "New class: a probe separates it from every older law",
    "new_by_vampire": "New class: fingerprint twins of old classes, all refuted by Vampire",
    "residue": "Residue: not settled within the time limits",
    "pending": "Not yet processed",
}


def report():
    laws, S, truth, cls, rep, keys, zero, old_by_key = setup()
    recs = {}
    for l in LOG.read_text().splitlines():            # later records (second pass) win
        if l.strip():
            r = json.loads(l)
            recs[r["id"]] = r
    rows, status = [], Counter()
    groups = {}                                          # fingerprint -> group id, over all new classes
    for i in range(N_OLD, len(laws)):
        r = recs.get(i + 1)
        extra = ""
        if r is None:
            st = "pending" if (zero[i] or keys[i] in old_by_key) else "new"
        else:
            st = {"collapse": "collapse", "joins": "joins", "not_joined": "new_by_vampire"}.get(r["status"], "residue")
            if st == "joins":
                extra = f"E{r['rep']}"
        if st in ("new", "new_by_vampire"):
            extra = f"group {groups.setdefault(keys[i], len(groups))}"
        status[st] += 1
        rows.append((i + 1, laws[i].text, st, extra))
    joined_classes = Counter(r["class"] for r in recs.values() if r["status"] == "joins")
    etp = {int(x) for x in (ROOT / "data" / "etp" / "order5_collapse_ids.txt").read_text().split()}
    ours = {row[0] for row in rows if row[2] == "collapse"}
    summary = {
        "new_laws": len(laws) - N_OLD,
        "status": {k: status.get(k, 0) for k in LABELS if status.get(k, 0) or k != "pending"},
        "labels": LABELS,
        "new_classes_lower_bound": len(groups),
        "new_classes_lower_bound_note": "new laws with different fingerprints cannot be equivalent, so the number "
                                        "of distinct fingerprints among new-class laws is a lower bound",
        "old_classes_that_gained_members": len(joined_classes),
        "etp_check": {"etp_collapse": len(etp), "ours": len(ours), "ours_not_etp": len(ours - etp),
                      "etp_not_ours": len(etp - ours),
                      "etp_not_ours_status": dict(Counter(row[2] for row in rows if row[0] in etp - ours))},
        "vampire_limits": "first pass 0.5-2 s per question; second look: finite-model search 0.3 s each way, then proof attempts 0.6 s each way",
        "etp_blueprint_for_comparison": {"collapse (only trivial models)": 19392,
                                         "only trivial finite models": 106,
                                         "unknown whether nontrivial finite models": 24},
    }
    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    with open(out / "order5_layer.tsv", "w", encoding="utf-8") as f:
        f.write("equation\tlaw\tstatus\tdetail\n")
        for row in rows:
            f.write("\t".join(map(str, row)) + "\n")
    (out / "order5_summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--retry", action="store_true")
    ap.add_argument("--max-minutes", type=float, default=30.0)
    ap.add_argument("--seconds", type=float, default=2.0)
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args()
    if a.report:
        report()
    elif a.retry:
        run_retry(a.seconds, a.workers, a.max_minutes)
    else:
        run(a.seconds, a.workers)
