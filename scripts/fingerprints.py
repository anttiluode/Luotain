"""Compute every law's response to every probe in the standard families.

    python scripts/fingerprints.py            # all 62,576 laws (a few minutes)
    python scripts/fingerprints.py --upto 4694

Writes cache/responses_<family>.npz with a packed bool matrix (laws x probes).
The cache is regenerable and not committed.
"""
import argparse
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from luotain.laws import load
from luotain.probes import standard_families, respond_all

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--upto", type=int, default=None, help="only the first N laws")
    args = ap.parse_args()
    CACHE.mkdir(exist_ok=True)
    laws = load()[: args.upto]
    for k, fam in enumerate(standard_families()):
        t = time.time()
        S = respond_all(laws, fam, progress=True)
        np.savez_compressed(CACHE / f"responses_{k}.npz", packed=np.packbits(S, axis=1),
                            nprobes=len(fam), name=fam.name)
        print(f"{fam.name}: {len(fam)} probes, {time.time() - t:.0f}s, "
              f"mean obey rate {S.mean():.4f}", flush=True)


def load_responses(k: int) -> tuple[np.ndarray, str]:
    z = np.load(CACHE / f"responses_{k}.npz")
    S = np.unpackbits(z["packed"], axis=1, count=int(z["nprobes"])).astype(bool)
    return S, str(z["name"])


if __name__ == "__main__":
    main()
