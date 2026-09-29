"""Compute every law's response to every probe in the standard families.

    python scripts/fingerprints.py            # all 62,576 laws (about 15 minutes on 2 cores)
    python scripts/fingerprints.py --upto 4694

Writes data/fingerprints/responses_<family>.npz, a packed bool matrix (laws x probes).
The files are committed (about 1 MB) so the later steps run without this one; the
computation is deterministic, so rerunning it reproduces them exactly.
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
FINGERPRINTS = ROOT / "data" / "fingerprints"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--upto", type=int, default=None, help="only the first N laws")
    args = ap.parse_args()
    FINGERPRINTS.mkdir(parents=True, exist_ok=True)
    laws = load()[: args.upto]
    for k, fam in enumerate(standard_families()):
        t = time.time()
        S = respond_all(laws, fam, progress=True)
        np.savez_compressed(FINGERPRINTS / f"responses_{k}.npz", packed=np.packbits(S, axis=1),
                            nprobes=len(fam), name=fam.name)
        print(f"{fam.name}: {len(fam)} probes, {time.time() - t:.0f}s, "
              f"mean obey rate {S.mean():.4f}", flush=True)


def load_responses(k: int) -> tuple[np.ndarray, str]:
    path = FINGERPRINTS / f"responses_{k}.npz"
    if not path.exists():
        raise SystemExit(f"{path} is missing. Run: python scripts/fingerprints.py")
    z = np.load(path)
    S = np.unpackbits(z["packed"], axis=1, count=int(z["nprobes"])).astype(bool)
    return S, str(z["name"])


if __name__ == "__main__":
    main()
