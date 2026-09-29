"""Step 4: Lean certificates for a random sample of every kind of claim.

The full claim sets are checked by the Python evaluator (tested against a brute-force
evaluator, and against all 8.17 million true edges of the published map with zero
false kills) and by Vampire.  Lean re-checks a random sample of each kind with its
own kernel, so none of those tools has to be trusted for the sampled claims:

    Calibration  published false edges, killed by a probe          (decide)
    Collapse     order-5 laws that force x = y                      (grind / replay)
    Joins        order-5 laws equivalent to an old law, both ways   (grind / replay)
    NewLaws      a new law and an old class, separated by a probe   (decide)
    SampleEdges  proved and refuted edges from the sample placement (both)

Theorems Lean cannot check (grind finds no proof, even replaying Vampire's steps)
are dropped from the files and counted, never silently kept.

    python scripts/lean_certs.py        # writes lean/Luotain/*.lean and checks them
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from luotain.kill import published_map
from luotain.laws import Law, load
from luotain.lean_emit import HEADER, law_def, proof, refutation, table_def, vampire_steps
from luotain.probes import Affine, all_tables, iso_reps, respond_affine, respond_tables
from luotain.prove import PROVED, vampire

LEAN = Path(__import__("os").environ.get("LUOTAIN_LEAN", "/tmp/leantc/lean-4.30.0-linux/bin/lean"))
OUT = ROOT / "lean" / "Luotain"
N_OLD = 4694
MAX_CASES = 20000                     # n ** vars budget for one decide


class Probes:
    """Small tables to certify refutations with, smallest first."""

    def __init__(self):
        self.t2 = iso_reps(all_tables(2))
        self.t3 = iso_reps(all_tables(3))
        self.aff = Affine.grid(range(2, 8))

    def witness(self, a: Law, b: Law):
        """A table obeying a and breaking b, small enough for decide, or None."""
        for T in (self.t2, self.t3):
            n = T.shape[1]
            if n ** max(a.nvars, b.nvars) > MAX_CASES:
                continue
            ok = respond_tables(a, T) & ~respond_tables(b, T)
            if ok.any():
                return T[int(np.flatnonzero(ok)[0])]
        ok = respond_affine(a, self.aff) & ~respond_affine(b, self.aff)
        for i in np.flatnonzero(ok):
            n = int(self.aff.n[i])
            if n ** max(a.nvars, b.nvars) <= MAX_CASES:
                return self.aff.table(int(i))
        return None


class Module:
    def __init__(self, name: str, laws: list[Law]):
        self.name, self.laws = name, laws
        self.tables: dict[bytes, str] = {}
        self.table_src: list[str] = []
        self.used: set[int] = set()
        self.thms: list[tuple[str, str, str]] = []      # (theorem name, kind, source)

    def table(self, T: np.ndarray) -> tuple[str, int]:
        key = T.tobytes() + bytes([len(T)])
        if key not in self.tables:
            nm = f"P{len(self.tables)}"
            self.tables[key] = nm
            self.table_src.append(table_def(nm, T))
        return self.tables[key], len(T)

    def refute(self, a: Law, b: Law, T: np.ndarray):
        nm, n = self.table(T)
        self.used |= {a.id, b.id}
        self.thms.append((f"not_{a.id}_{b.id}", "refutation", refutation(nm, n, a, b)))

    def prove(self, a: Law, b: Law, steps=None):
        self.used |= {a.id, b.id}
        self.thms.append((f"imp_{a.id}_{b.id}", "proof", proof(a, b, steps)))

    def source(self, keep=None) -> str:
        parts = [HEADER, f"namespace Luotain.{self.name}", ""]
        parts += [law_def(self.laws[i - 1]) for i in sorted(self.used)]
        parts += [""] + self.table_src + [""]
        parts += [src for nm, kind, src in self.thms if keep is None or nm in keep]
        parts += ["", f"end Luotain.{self.name}"]
        return "\n\n".join(parts) + "\n"


def check(path: Path) -> set[int]:
    """Line numbers with errors."""
    r = subprocess.run([str(LEAN), str(path)], capture_output=True, text=True, cwd=path.parent)
    return {int(m.group(1)) for m in re.finditer(rf"{re.escape(path.name)}:(\d+):\d+: error", r.stdout + r.stderr)}


def failing_theorems(src: str, bad_lines: set[int]) -> set[str]:
    names, current = {}, None
    for ln, line in enumerate(src.splitlines(), start=1):
        m = re.match(r"theorem (\S+)", line)
        if m:
            current = m.group(1)
        names[ln] = current
    return {names.get(ln) for ln in bad_lines} - {None}


def build(mod: Module, laws: list[Law]) -> dict:
    """Write, check, retry failed proofs with Vampire's steps, drop what still fails."""
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{mod.name}.lean"
    src = mod.source()
    path.write_text(src)
    bad = failing_theorems(src, check(path))
    replayed = 0
    if bad:
        new = []
        for nm, kind, s in mod.thms:
            if nm in bad and kind == "proof":
                a, b = (int(x) for x in nm.split("_")[1:])
                v, out = vampire(laws[a - 1], laws[b - 1], 10, want_proof=True)
                if v == PROVED:
                    s = proof(laws[a - 1], laws[b - 1], vampire_steps(out))
                    replayed += 1
            new.append((nm, kind, s))
        mod.thms = new
        src = mod.source()
        path.write_text(src)
        bad = failing_theorems(src, check(path))
    keep = {nm for nm, _, _ in mod.thms} - bad
    for _ in range(5):                                   # drop whatever still fails, until clean
        src = mod.source(keep)
        path.write_text(src)
        still = failing_theorems(src, check(path))
        if not still:
            break
        keep -= still
        bad |= still
    assert not check(path), f"{path} still has errors"
    kinds = {}
    for nm, kind, _ in mod.thms:
        d = kinds.setdefault(kind, {"attempted": 0, "checked": 0})
        d["attempted"] += 1
        d["checked"] += nm in keep
    return {"module": mod.name, **kinds, "retried_with_vampire_steps": replayed, "dropped": sorted(bad)}


def main():
    laws = load()
    rng = np.random.default_rng(7)
    probes = Probes()
    truth, code, names = published_map()
    report = []

    # 1. calibration: published false edges, killed by a small probe
    mod = Module("Calibration", laws)
    off = ~np.eye(N_OLD, dtype=bool)
    F = np.argwhere(~truth & off)
    for a, b in F[rng.choice(len(F), 400, replace=False)]:
        T = probes.witness(laws[a], laws[b])
        if T is not None:
            mod.refute(laws[a], laws[b], T)
        if len(mod.thms) >= 60:
            break
    report.append(build(mod, laws))

    recs = [json.loads(l) for l in (ROOT / "cache" / "place.jsonl").read_text().splitlines() if l.strip()]
    # 2. collapse: order-5 laws that force x = y
    mod = Module("Collapse", laws)
    col = [r["id"] for r in recs if r["status"] == "collapse"]
    for i in rng.choice(col, 80, replace=False):
        mod.prove(laws[i - 1], laws[1])
    report.append(build(mod, laws))

    # 3. joins: equivalent to an old law, both directions
    mod = Module("Joins", laws)
    jn = [r for r in recs if r["status"] == "joins"]
    for k in rng.choice(len(jn), 60, replace=False):
        r = jn[k]
        mod.prove(laws[r["id"] - 1], laws[r["rep"] - 1])
        mod.prove(laws[r["rep"] - 1], laws[r["id"] - 1])
    report.append(build(mod, laws))

    # 4. new laws: separated from a random old class by a probe
    mod = Module("NewLaws", laws)
    tsv = (ROOT / "results" / "order5_layer.tsv").read_text(encoding="utf-8").splitlines()[1:]
    new_ids = [int(l.split("\t")[0]) for l in tsv if l.split("\t")[2] == "new"]
    tries = 0
    while len(mod.thms) < 60 and tries < 2000:
        tries += 1
        i = int(rng.choice(new_ids))
        j = int(rng.integers(0, N_OLD))
        a, b = laws[i - 1], laws[j]
        T = probes.witness(a, b)
        if T is not None:
            mod.refute(a, b, T)
            continue
        T = probes.witness(b, a)
        if T is not None:
            mod.refute(b, a, T)
    report.append(build(mod, laws))

    # 5. sample placement: proved parents/children and probe-refuted edges
    mod = Module("SampleEdges", laws)
    se = [json.loads(l) for l in (ROOT / "results" / "sample_edges.jsonl").read_text().splitlines() if l.strip()]
    for r in [se[k] for k in rng.choice(len(se), min(30, len(se)), replace=False)]:
        L = laws[r["id"] - 1]
        for p in r["parents"][:2]:
            mod.prove(L, laws[p - 1])
        for c in r["children"][:1]:
            mod.prove(laws[c - 1], L)
        j = int(rng.integers(0, N_OLD))
        T = probes.witness(L, laws[j])
        if T is not None:
            mod.refute(L, laws[j], T)
    report.append(build(mod, laws))

    root = ROOT / "lean" / "Luotain.lean"
    root.write_text("".join(f"import Luotain.{m['module']}\n" for m in report))
    (ROOT / "results" / "lean_certificates.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
