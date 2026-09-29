"""A few concrete findings for the README, read off the results files.

    python scripts/findings.py   # -> results/findings.json
"""
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from luotain.kill import classes, published_map
from luotain.laws import load


def main():
    laws = load()
    truth, _, _ = published_map()
    cls = classes(truth)
    size = Counter(cls.tolist())
    rows = [l.split("\t") for l in (ROOT / "results" / "order5_layer.tsv").read_text(encoding="utf-8").splitlines()[1:]]

    joins = Counter(r[3] for r in rows if r[2] == "joins")
    top_joined = [{"class_rep": rep, "law": laws[int(rep[1:]) - 1].text,
                   "old_members": size[int(cls[int(rep[1:]) - 1])], "new_members": n}
                  for rep, n in joins.most_common(6)]

    groups = Counter(r[3] for r in rows if r[2] in ("new", "new_by_vampire"))
    group_sizes = Counter(groups.values())
    new_rows = [r for r in rows if r[2] in ("new", "new_by_vampire")]
    few_vars = sorted(new_rows, key=lambda r: (laws[int(r[0]) - 1].nvars, int(r[0])))[:8]

    res = np.load(ROOT / "results" / "calibration_residue.npz")["pairs"]
    hardest = Counter(res[:, 0].tolist()).most_common(5)
    findings = {
        "old_classes_with_most_new_members": top_joined,
        "new_class_group_sizes": {str(k): v for k, v in sorted(group_sizes.items())[:10]},
        "largest_new_group": max(groups.values()) if groups else 0,
        "new_laws_with_fewest_variables": [{"equation": int(r[0]), "law": r[1], "status": r[2]} for r in few_vars],
        "calibration_residue_most_frequent_source_laws": [
            {"equation": int(e), "law": laws[int(e) - 1].text, "residue_edges_from_it": n} for e, n in hardest],
    }
    (ROOT / "results" / "findings.json").write_text(json.dumps(findings, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(findings, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
