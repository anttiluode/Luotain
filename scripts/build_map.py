"""Step 5: the map.

Lays the classes out by their Stone pairings on the 3,330 kinds of 3-element table
(the fraction of variable choices each table satisfies; the idea and the use of PCA
follow Berlioz & Melliès, "The latent space of equational theories", 2026), and
writes the self-contained page site/index.html from site/template.html.

    python scripts/build_map.py
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from luotain.kill import classes, hasse, published_map
from luotain.laws import load
from luotain.probes import all_tables, iso_reps, respond_tables

N_OLD = 4694


def main():
    laws = load()
    truth, _, _ = published_map()
    cls = classes(truth)
    k = int(cls.max()) + 1
    members = [np.flatnonzero(cls == c) for c in range(k)]
    rep = [int(m[0]) for m in members]
    edges = hasse(truth, cls)

    rows = (ROOT / "results" / "order5_layer.tsv").read_text(encoding="utf-8").splitlines()[1:]
    status = {}
    group_rep = {}
    joins = {}
    residue = []
    for line in rows:
        eq, text, st, detail = line.split("\t")
        eq = int(eq)
        status[eq] = st
        if st in ("new", "new_by_vampire"):
            group_rep.setdefault(detail, eq)
        if st == "joins":
            joins.setdefault(int(detail[1:]), []).append(eq)
        if st == "residue":
            residue.append(eq)

    new_reps = sorted(group_rep.values())
    T3 = iso_reps(all_tables(3))
    feats_old = np.array([respond_tables(laws[i], T3, stone=True) for i in rep], dtype=np.float32)
    feats_new = np.array([respond_tables(laws[i - 1], T3, stone=True) for i in new_reps], dtype=np.float32)
    feats_res = np.array([respond_tables(laws[i - 1], T3, stone=True) for i in residue], dtype=np.float32).reshape(-1, len(T3))
    X = np.vstack([feats_old, feats_new])
    # x = x and x = y sit at the two extremes (every law implies the first, the second implies
    # every law); fit the projection without them so they do not squash everything else
    fit = np.ones(len(X), dtype=bool)
    fit[[int(cls[0]), int(cls[1])]] = False
    mu = X[fit].mean(axis=0)
    U, s, Vt = np.linalg.svd(X[fit] - mu, full_matrices=False)
    xy = (X - mu) @ Vt[:2].T
    xy_res = (feats_res - mu) @ Vt[:2].T if len(residue) else np.zeros((0, 2))
    explained = [round(float(v), 3) for v in s[:2].astype(np.float64) ** 2 / (s.astype(np.float64) ** 2).sum()]

    sample = []
    se = ROOT / "results" / "sample_edges.jsonl"
    if se.exists():
        sample = [json.loads(l) for l in se.read_text().splitlines() if l.strip()]
    calib = json.loads((ROOT / "results" / "calibration.json").read_text())
    summary = json.loads((ROOT / "results" / "order5_summary.json").read_text())
    certs = ROOT / "results" / "lean_certificates.json"
    certs_text = ""
    if certs.exists():
        rep_ = json.loads(certs.read_text())
        ref = sum(m.get("refutation", {}).get("checked", 0) for m in rep_)
        prf = sum(m.get("proof", {}).get("checked", 0) for m in rep_)
        prf_try = sum(m.get("proof", {}).get("attempted", 0) for m in rep_)
        certs_text = (f"Who checked what: every probe verdict comes from the Python evaluator, which matches a brute-force "
                      f"evaluator and kills none of the published map's true implications. Every proof comes from the "
                      f"Vampire prover. Lean's kernel re-checks a random sample: {ref} probe refutations, and "
                      f"{prf} of {prf_try} sampled proofs (the rest stay Vampire-only).")
    codes = {"collapse": "c", "joins": "j", "new": "n", "new_by_vampire": "v", "residue": "r", "pending": "p"}
    status_str = "o" * N_OLD + "".join(codes.get(status.get(i, "pending"), "p") for i in range(N_OLD + 1, len(laws) + 1))

    rep_index = {r + 1: c for c, r in enumerate(rep)}
    labels = summary["labels"]
    data = {
        "old": [{"x": round(float(xy[c, 0]), 4), "y": round(float(xy[c, 1]), 4),
                 "n": int(len(members[c])), "eq": rep[c] + 1, "law": laws[rep[c]].text,
                 "joined": len(joins.get(rep[c] + 1, [])) + (int(summary["status"].get("collapse", 0)) if c == int(cls[1]) else 0)}
                for c in range(k)],
        "new": [{"x": round(float(xy[k + j, 0]), 4), "y": round(float(xy[k + j, 1]), 4),
                 "eq": e, "law": laws[e - 1].text} for j, e in enumerate(new_reps)],
        "residue": [{"x": round(float(p[0]), 4), "y": round(float(p[1]), 4), "eq": e, "law": laws[e - 1].text}
                    for p, e in zip(xy_res, residue)],
        "hasse": edges,
        "collapse_class": int(cls[1]),
        "trivial_class": int(cls[0]),
        "layer_rows": [[labels[st], n] for st, n in summary["status"].items() if n],
        "status_str": status_str,
        "status_names": {v: labels.get(k, "an older law (at most four multiplications)") for k, v in codes.items()} | {"o": "a law with at most four multiplications, drawn under its class"},
        "certs_text": certs_text,
        "calibration": calib,
        "summary": summary,
        "sample": [{"eq": r["id"], "parents": [rep_index[p] for p in r["parents"] if p in rep_index],
                    "children": [rep_index[c] for c in r["children"] if c in rep_index],
                    "implies": r["implies"], "implied_by": r["implied_by"],
                    "open": len(r["open_up"]) + len(r["open_down"])} for r in sample],
        "pca_explained": explained,
    }
    js = "window.LUOTAIN = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";"
    page = (ROOT / "site" / "template.html").read_text(encoding="utf-8").replace("/*DATA*/", js)
    (ROOT / "site" / "index.html").write_text(page, encoding="utf-8")
    print(f"wrote site/index.html ({len(page.encode()) / 1e6:.1f} MB): {k} old classes, {len(new_reps)} new groups, "
          f"{len(residue)} residue, {len(edges)} cover edges, PCA explained {explained}")


if __name__ == "__main__":
    main()
