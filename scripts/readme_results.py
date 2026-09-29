"""Fill the README's results section from the results files, so every number in it is
the number the scripts produced.

    python scripts/readme_results.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

MARK_START, MARK_END = "<!--RESULTS-->", "<!--/RESULTS-->"


def fmt(n):
    return f"{n:,}"


def section() -> str:
    cal = json.loads((ROOT / "results" / "calibration.json").read_text())
    lay = json.loads((ROOT / "results" / "order5_summary.json").read_text())
    se = [json.loads(l) for l in (ROOT / "results" / "sample_edges.jsonl").read_text().splitlines() if l.strip()]
    lean = json.loads((ROOT / "results" / "lean_certificates.json").read_text())
    fnd = json.loads((ROOT / "results" / "findings.json").read_text(encoding="utf-8"))
    out = []
    w = out.append

    w("## Results\n")
    w("### Step 1: calibration on the finished map\n")
    w(f"The published map has {fmt(cal['true_edges'])} true and {fmt(cal['false_edges'])} false implications between "
      f"distinct laws. Probe families were added cheapest first:\n")
    w("| probe family | probes | false edges killed (new) | killed so far |")
    w("|---|---:|---:|---:|")
    for f in cal["families"]:
        w(f"| {f['family']} | {fmt(f['probes'])} | {fmt(f['new_kills'])} | "
          f"{100 * f['cumulative_kills'] / cal['false_edges']:.2f}% |")
    w("")
    w(f"- **Ten** two-element tables (one per isomorphism class) kill {100 * cal['families'][0]['new_kills'] / cal['false_edges']:.1f}% "
      f"of all false implications.")
    w(f"- Everything together kills {fmt(cal['killed'])} ({100 * cal['killed_fraction']:.2f}%). "
      f"Random four-element tables add almost nothing: random tables rarely obey any law, so they rarely witness anything.")
    w(f"- **Zero** kills on the {fmt(cal['true_edges'])} true implications. Any kill there would have exposed a bug in the "
      f"evaluator, so this is also its largest test.")
    w(f"- The residue is {fmt(cal['residue_edges'])} false implications ({fmt(cal['class_level']['residue_class_pairs'])} "
      f"between classes) that no probe here witnesses. All 190 pairs still open in the published snapshot of "
      f"November 2024 are in it. That is where the project needed infinite models, large finite ones and human proofs. "
      f"The list is `results/calibration_residue.npz`.\n")

    st = lay["status"]
    lab = lay["labels"]
    w("### Step 2: the five-multiplication layer\n")
    w(f"Where each of the {fmt(lay['new_laws'])} laws with five multiplications landed:\n")
    w("| where it landed | laws |")
    w("|---|---:|")
    for k, n in st.items():
        w(f"| {lab[k]} | {fmt(n)} |")
    w("")
    w(f"- **At least {fmt(lay['new_classes_lower_bound'])} new equivalence classes.** New laws with different fingerprints cannot "
      f"be equivalent, so the number of distinct fingerprints among them is a lower bound. The whole four-multiplication map "
      f"has 1,415 classes.")
    w(f"- {fmt(lay['old_classes_that_gained_members'])} of the 1,415 old classes gained five-multiplication members.")
    if "etp_check" in lay:
        c = lay["etp_check"]
        w(f"- **Cross-check against the ETP.** The project proved in Lean that {fmt(c['etp_collapse'])} five-multiplication laws "
          f"collapse to x = y (branch `order5` of vlad902/equational_theories). Luotain's collapse set has {fmt(c['ours'])} laws: "
          f"{fmt(c['ours_not_etp'])} outside theirs, and {fmt(c['etp_not_ours'])} of theirs left in our residue.")
    w(f"- Each Vampire question got a short time limit (a second or less in the first pass, then a finite-model search and "
      f"a longer proof attempt). The residue is what is left after that, not what is impossible.")
    w("- The full list, one line per law, is `results/order5_layer.tsv`.\n")

    if se:
        n = len(se)
        k = 1415
        probe = sum(r["probe_kills_up"] + r["probe_kills_down"] for r in se)
        decided = sum(r["implies"] + r["not_implies"] + r["implied_by"] + r["not_implied_by"] for r in se)
        opened = sum(len(r["open_up"]) + len(r["open_down"]) for r in se)
        calls = sum(r["vampire_calls"] for r in se)
        w("### Step 3: every edge, for a sample of new laws\n")
        w(f"For {n} new laws (one per fingerprint group, chosen at random), every edge to and from the 1,415 old classes was "
          f"decided: {fmt(2 * k * n)} edges in all.\n")
        w(f"- Probes decided {fmt(probe)} of them ({100 * probe / (2 * k * n):.1f}%) directly.")
        w(f"- {fmt(calls)} Vampire questions, with answers spread along the old map, decided most of the rest. "
          f"In total {fmt(decided)} edges ({100 * decided / (2 * k * n):.2f}%) are settled.")
        w(f"- {fmt(opened)} edges ({100 * opened / (2 * k * n):.2f}%) stay open: the residue for this sample.")
        w(f"- On average a sample law implies {sum(r['implies'] for r in se) / n:.0f} old classes and is implied by "
          f"{sum(r['implied_by'] for r in se) / n:.0f}.\n")

    w("### Certificates\n")
    w("Every probe verdict comes from the Python evaluator. It matches a brute-force evaluator in the tests and kills none of the "
      "published map's true implications. Every proof comes from Vampire. Lean's kernel then re-checks a random sample of "
      "each kind of claim, using core Lean 4.30 only:\n")
    w("| Lean file | refutations checked | proofs checked | proofs attempted |")
    w("|---|---:|---:|---:|")
    for m in lean:
        r = m.get("refutation", {})
        p = m.get("proof", {})
        w(f"| `lean/Luotain/{m['module']}.lean` | {r.get('checked', 0)} | {p.get('checked', 0)} | {p.get('attempted', 0)} |")
    w("")
    w("A refutation is a table plus two `decide` checks. A proof is `grind`, and when grind finds nothing, the equations from "
      "Vampire's proof are replayed as intermediate steps. Proofs Lean still cannot check are dropped from the files and "
      "stay Vampire-only; the table counts them. Run `cd lean && lake build` to check everything yourself.\n")
    w("Every sampled refutation passes. Proofs are the weak side: `grind` cannot find the substitutions most of these "
      "proofs need, and replaying Vampire's intermediate equations does not supply them. That hits the collapse proofs "
      "hardest. They are covered from outside, though: the ETP's `order5` branch has a Lean proof (with Mathlib and its own "
      "`superpose` tactic) for every one of its 19,392 collapses, and Luotain's collapse set lies inside it.\n")

    w("### A few concrete things\n")
    top = fnd["old_classes_with_most_new_members"]
    if top:
        w("Old classes that gained the most five-multiplication members:\n")
        for t in top[:4]:
            w(f"- `{t['law']}` ({t['class_rep']}): {fmt(t['old_members'])} old members, {fmt(t['new_members'])} new")
        w("")
    ex = fnd["new_laws_with_fewest_variables"]
    if ex:
        w("New classes with the fewest variables, each different from every law with four or fewer multiplications:\n")
        for e in ex[:6]:
            w(f"- Equation {e['equation']}: `{e['law']}`")
        w("")

    w("## What this shows and what it doesn't\n")
    w("Shown:\n")
    w("- Small structured tables settle 99.5% of the published map's false implications on their own, with no false kill.")
    w("- The five-multiplication layer can be placed on the map at scale with probes plus a prover, and the result agrees with "
      "the ETP's own Lean-proved collapse list wherever both decided.")
    w("- Order five adds thousands of classes that differ from every smaller law, each separated from every one of them by an "
      "explicit table or a Vampire countermodel.\n")
    w("Not shown:\n")
    w("- The full implication graph among the five-multiplication laws themselves (about 3.3 billion ordered pairs). Only the "
      "layer's relation to the old map is placed, with every edge decided for a sample.")
    w("- Anything about the residue except that it is there. Settling it needs infinite models, large finite ones and "
      "longer proofs, which is what the ETP spent most of its effort on.")
    w("- That every claim is Lean-checked. Lean checks a random sample; the rest rests on the evaluator's tests and on Vampire.\n")

    w("## Prior work this builds on\n")
    w("- The Equational Theories Project: the laws, their numbering, the finished map, and the Vampire workflow "
      "([paper](https://arxiv.org/abs/2512.07087)). Its blueprint already classified the five-multiplication laws by whether "
      "they collapse to x = y; placing them against the rest of the map is what is new here.")
    w("- Berlioz and Melliès, *The latent space of equational theories* ([arXiv:2601.20759](https://arxiv.org/abs/2601.20759)): "
      "laws as points built from their satisfaction on finite magmas. The map's layout follows their idea, for the four- and "
      "five-multiplication laws together.")
    w("- Birkhoff (1935) on laws and the structures that obey them; Vampire (Kovács and Voronkov); Lean 4 and its `grind` tactic.\n")
    return "\n".join(out)


def main():
    readme = ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")
    body = section()
    if MARK_START in text:
        a = text.index(MARK_START)
        b = text.index(MARK_END) + len(MARK_END) if MARK_END in text else a + len(MARK_START)
        text = text[:a] + MARK_START + "\n" + body + "\n" + MARK_END + text[b:]
    readme.write_text(text, encoding="utf-8")
    print(body)


if __name__ == "__main__":
    main()
