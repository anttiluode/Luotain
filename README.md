# Luotain

*Luotain* is Finnish for a sounding probe. This repository maps which equational laws imply which, by sending small multiplication tables into the space of laws as probes, and asking a theorem prover about whatever the probes cannot decide.

A law here is an equation about one binary operation ◇, such as `x ◇ (y ◇ z) = (x ◇ y) ◇ z`, that must hold for every choice of the variables. Law A *implies* law B when every structure that obeys A also obeys B. The [Equational Theories Project](https://github.com/teorth/equational_theories) (ETP) settled every one of the 22,028,942 implications between the 4,694 laws with at most four multiplications. Luotain does two things with that finished map:

1. **Calibrates** how far pure probing gets on it, against the published answers.
2. **Extends** it to the 57,882 laws with five multiplications, which nobody has placed on the map. For each new law it decides whether the law is equivalent to an older one or opens a new class, and for a sample of new laws it decides every edge to the old map.

**The map:** [anttiluode.github.io/Luotain](https://anttiluode.github.io/Luotain/), one page built from `site/index.html`.

Every claim carries a certificate that can be checked without trusting this code: a table (for "A does not imply B") or a Vampire proof (for "A implies B"). Lean's kernel re-checks a random sample of both.

## The idea

A probe is a small multiplication table. It obeys some laws and breaks others. If A implies B, every table that obeys A obeys B. So **one table that obeys A and breaks B proves that A does not imply B**, and anyone can check that by hand.

Give each law its *fingerprint*: the set of probes that obey it. Then "A implies B" is only possible when A's fingerprint is contained in B's. Two laws with different fingerprints cannot be equivalent. The space of laws exists before anyone probes it (Birkhoff showed in 1935 that a set of laws and the structures obeying it determine each other); the probes read its coordinates.

What no probe separates and no proof settles is the **residue**. That is where the hard mathematics is.

<!--RESULTS-->
## Results

### Step 1: calibration on the finished map

The published map has 8,173,585 true and 13,855,357 false implications between distinct laws. Probe families were added cheapest first:

| probe family | probes | false edges killed (new) | killed so far |
|---|---:|---:|---:|
| all 2-element tables | 10 | 12,560,783 | 90.66% |
| all 3-element tables | 3,330 | 1,035,338 | 98.13% |
| affine x◇y = ax+by+c mod n, n <= 12 | 6,083 | 193,530 | 99.53% |
| 2,000 random 4-element tables | 2,000 | 30 | 99.53% |

- **Ten** two-element tables (one per isomorphism class) kill 90.7% of all false implications.
- Everything together kills 13,789,681 (99.53%). Random four-element tables add almost nothing: random tables rarely obey any law, so they rarely witness anything.
- **Zero** kills on the 8,173,585 true implications. Any kill there would have exposed a bug in the evaluator, so this is also its largest test.
- The residue is 65,676 false implications (20,163 between classes) that no probe here witnesses. All 190 pairs still open in the published snapshot of November 2024 are in it. That is where the project needed infinite models, large finite ones and human proofs. The list is `results/calibration_residue.npz`.

### Step 2: the five-multiplication layer

Where each of the 57,882 laws with five multiplications landed:

| where it landed | laws |
|---|---:|
| Collapse to x = y (Vampire proof; no probe obeys them) | 19,385 |
| Equivalent to an older law (Vampire proofs both ways) | 17,536 |
| New class: a probe separates it from every older law | 15,858 |
| New class: fingerprint twins of old classes, all refuted by Vampire | 3,825 |
| Residue: not settled within the time limits | 1,278 |

- **At least 9,086 new equivalence classes.** New laws with different fingerprints cannot be equivalent, so the number of distinct fingerprints among them is a lower bound. The whole four-multiplication map has 1,415 classes.
- 446 of the 1,415 old classes gained five-multiplication members.
- **Cross-check against the ETP.** The project proved in Lean that 19,392 five-multiplication laws collapse to x = y (branch `order5` of vlad902/equational_theories). Luotain's collapse set has 19,385 laws: 0 outside theirs, and 7 of theirs left in our residue.
- Each Vampire question got a short time limit (a second or less in the first pass, then a finite-model search and a longer proof attempt). The residue is what is left after that, not what is impossible.
- The full list, one line per law, is `results/order5_layer.tsv`.

### Step 3: every edge, for a sample of new laws

For 150 new laws (one per fingerprint group, chosen at random), every edge to and from the 1,415 old classes was decided: 424,500 edges in all.

- Probes decided 418,667 of them (98.6%) directly.
- 3,239 Vampire questions, with answers spread along the old map, decided most of the rest. In total 423,446 edges (99.75%) are settled.
- 1,054 edges (0.25%) stay open: the residue for this sample.
- On average a sample law implies 3 old classes and is implied by 18.

### Certificates

Every probe verdict comes from the Python evaluator. It matches a brute-force evaluator in the tests and kills none of the published map's true implications. Every proof comes from Vampire. Lean's kernel then re-checks a random sample of each kind of claim, using core Lean 4.30 only:

| Lean file | refutations checked | proofs checked | proofs attempted |
|---|---:|---:|---:|
| `lean/Luotain/Calibration.lean` | 60 | 0 | 0 |
| `lean/Luotain/Collapse.lean` | 0 | 0 | 80 |
| `lean/Luotain/Joins.lean` | 0 | 38 | 120 |
| `lean/Luotain/NewLaws.lean` | 60 | 0 | 0 |
| `lean/Luotain/SampleEdges.lean` | 29 | 41 | 61 |

A refutation is a table plus two `decide` checks. A proof is `grind`, and when grind finds nothing, the equations from Vampire's proof are replayed as intermediate steps. Proofs Lean still cannot check are dropped from the files and stay Vampire-only; the table counts them. Run `cd lean && lake build` to check everything yourself.

Every sampled refutation passes. Proofs are the weak side: `grind` cannot find the substitutions most of these proofs need, and replaying Vampire's intermediate equations does not supply them. That hits the collapse proofs hardest. They are covered from outside, though: the ETP's `order5` branch has a Lean proof (with Mathlib and its own `superpose` tactic) for every one of its 19,392 collapses, and Luotain's collapse set lies inside it.

### A few concrete things

Old classes that gained the most five-multiplication members:

- `x ◇ x = y ◇ z` (E41): 419 old members, 5,103 new
- `x = y ◇ (x ◇ x)` (E13): 112 old members, 1,181 new
- `x = (x ◇ x) ◇ y` (E24): 112 old members, 1,181 new
- `x = y ◇ (x ◇ (x ◇ x))` (E62): 76 old members, 891 new

New classes with the fewest variables, each different from every law with four or fewer multiplications:

- Equation 4695: `x = x ◇ (x ◇ (x ◇ (x ◇ (x ◇ x))))`
- Equation 5572: `x = x ◇ (x ◇ (x ◇ ((x ◇ x) ◇ x)))`
- Equation 6449: `x = x ◇ (x ◇ ((x ◇ x) ◇ (x ◇ x)))`
- Equation 7326: `x = x ◇ (x ◇ ((x ◇ (x ◇ x)) ◇ x))`
- Equation 8203: `x = x ◇ (x ◇ (((x ◇ x) ◇ x) ◇ x))`
- Equation 9080: `x = x ◇ ((x ◇ x) ◇ (x ◇ (x ◇ x)))`

## What this shows and what it doesn't

Shown:

- Small structured tables settle 99.5% of the published map's false implications on their own, with no false kill.
- The five-multiplication layer can be placed on the map at scale with probes plus a prover, and the result agrees with the ETP's own Lean-proved collapse list wherever both decided.
- Order five adds thousands of classes that differ from every smaller law, each separated from every one of them by an explicit table or a Vampire countermodel.

Not shown:

- The full implication graph among the five-multiplication laws themselves (about 3.3 billion ordered pairs). Only the layer's relation to the old map is placed, with every edge decided for a sample.
- Anything about the residue except that it is there. Settling it needs infinite models, large finite ones and longer proofs, which is what the ETP spent most of its effort on.
- That every claim is Lean-checked. Lean checks a random sample; the rest rests on the evaluator's tests and on Vampire.

## Prior work this builds on

- The Equational Theories Project: the laws, their numbering, the finished map, and the Vampire workflow ([paper](https://arxiv.org/abs/2512.07087)). Its blueprint already classified the five-multiplication laws by whether they collapse to x = y; placing them against the rest of the map is what is new here.
- Berlioz and Melliès, *The latent space of equational theories* ([arXiv:2601.20759](https://arxiv.org/abs/2601.20759)): laws as points built from their satisfaction on finite magmas. The map's layout follows their idea, for the four- and five-multiplication laws together.
- Birkhoff (1935) on laws and the structures that obey them; Vampire (Kovács and Voronkov); Lean 4 and its `grind` tactic.

<!--/RESULTS-->

## Reproduce

```sh
pip install -r requirements.txt pytest
sh scripts/get_tools.sh                  # downloads the Vampire prover into tools/
python -m pytest -q tests                # evaluator and published-map checks (~30 s)
python scripts/fingerprints.py           # every law against every probe (~15 min)
python scripts/calibrate.py              # step 1 -> results/calibration.json
python scripts/place.py                  # step 2, resumable (~45 min on 2 cores)
python scripts/place.py --retry          # second look at what is left
python scripts/place.py --report         # -> results/order5_layer.tsv, order5_summary.json
python scripts/edges.py --sample 60      # step 3 -> results/sample_edges.jsonl
python scripts/lean_certs.py             # step 4 -> lean/Luotain/*.lean, checked on the spot
python scripts/build_map.py              # the map -> site/index.html
cd lean && lake build                    # Lean's kernel checks every certificate
```

## Layout

```text
luotain/laws.py        parse the ETP's equations, print them, emit TPTP and Lean
luotain/probes.py      probe families and the vectorised evaluator (plus the affine shortcut)
luotain/kill.py        kill matrices, the published map, classes, cover edges
luotain/prove.py       Vampire wrapper
luotain/lean_emit.py   Lean certificates: tables checked by decide, proofs by grind
scripts/               the steps above, in order
data/etp/              the ETP's equation list (order <= 5) and outcome matrix, Apache-2.0
results/               everything measured, as JSON/TSV
lean/                  the Lean certificates (core Lean 4.30, no Mathlib)
site/index.html        the map, one self-contained page
tests/                 evaluator against brute force, parser round trip, published-map checks
```

## License

Code: MIT. `data/etp/` is from the Equational Theories Project and keeps its Apache-2.0 license (`data/etp/LICENSE-ETP`).
