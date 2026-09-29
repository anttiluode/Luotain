"""Proofs and countermodels from the Vampire prover (the one the ETP used most).

Vampire answers 'Theorem' (the implication holds, with a proof), 'CounterSatisfiable'
(it found a model where it fails) or runs out of time.  Probes kill most false
implications before Vampire is asked; Vampire is spent on what the probes leave.

Set LUOTAIN_VAMPIRE to the binary, or put it in tools/ (scripts/get_tools.sh on Linux,
run_overnight.bat on Windows, which fetches vampire.exe).
"""
from __future__ import annotations

import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .laws import Law, tptp_problem

ROOT = Path(__file__).resolve().parent.parent
_DEFAULT = ROOT / "tools" / ("vampire.exe" if os.name == "nt" else "vampire")
VAMPIRE = os.environ.get("LUOTAIN_VAMPIRE", str(_DEFAULT))

PROVED, REFUTED, UNKNOWN = "proved", "refuted", "unknown"


def require_vampire():
    """Stop with a clear message instead of reporting every question as 'unknown'."""
    if not Path(VAMPIRE).exists():
        raise SystemExit(f"Vampire not found at {VAMPIRE}. Run scripts/get_tools.sh (Linux) or "
                         f"run_overnight.bat (Windows), or set LUOTAIN_VAMPIRE.")


def vampire(hyp: Law, goal: Law, seconds: float = 5.0, mode: str = "casc",
            want_proof: bool = False) -> tuple[str, str]:
    """(verdict, output).  mode 'casc' is Vampire's portfolio; 'fmb' is its finite-model builder."""
    args = [VAMPIRE, "-t", f"{seconds:g}"]
    args += ["--mode", "casc"] if mode == "casc" else ["-sa", "fmb"]
    if not want_proof:
        args += ["-p", "off"]
    try:
        out = subprocess.run(args, input=tptp_problem(hyp, goal), capture_output=True, text=True,
                             timeout=seconds * 2 + 10).stdout
    except subprocess.TimeoutExpired:
        return UNKNOWN, ""
    if "SZS status Theorem" in out:
        return PROVED, out
    if "SZS status CounterSatisfiable" in out:
        return REFUTED, out
    return UNKNOWN, out


def vampire_many(pairs: list[tuple[Law, Law]], seconds: float = 5.0, mode: str = "casc",
                 workers: int = 2) -> list[str]:
    def one(p):
        return vampire(p[0], p[1], seconds, mode)[0]
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(one, pairs))
