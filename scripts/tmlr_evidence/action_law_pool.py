"""Pool the per-seed action-law checks (``action_law_check.py`` outputs).

For each tested quantity, sums observed and expected counts over seeds and
divides by the pooled binomial SD (the per-seed SD is recovered as
(observed − expected) / z). Writes one JSON with the pooled z per quantity.

Usage::

    python scripts/tmlr_evidence/action_law_pool.py --inputs A.json B.json --out pooled.json
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inputs", nargs="+", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    tot: dict[str, list[float]] = {}
    seeds, decisions = [], 0.0
    for f in a.inputs:
        d = json.loads(f.read_text())
        for seed, r in d["per_seed"].items():
            seeds.append(int(seed))
            decisions += sum(v["observed"] for k, v in r.items() if k.startswith("channel_"))
            for k, v in r.items():
                if not (k.startswith("channel_") or k == "explored"):
                    continue
                o, e, z = v["observed"], v["expected"], v["z"]
                t = tot.setdefault(k, [0.0, 0.0, 0.0])
                t[0] += o
                t[1] += e
                t[2] += ((o - e) / z) ** 2 if z else 0.0
    pooled = {k: {"observed": o, "expected": e, "z": (o - e) / math.sqrt(var)}
              for k, (o, e, var) in tot.items()}
    rec = {"inputs": [str(p) for p in a.inputs], "seeds": sorted(seeds),
           "month0_decisions": int(decisions), "pooled": pooled,
           "max_abs_pooled_z": max(abs(v["z"]) for v in pooled.values())}
    a.out.write_text(json.dumps(rec, indent=2))
    print(json.dumps({k: round(v["z"], 2) for k, v in pooled.items()}),
          "decisions", int(decisions))


if __name__ == "__main__":
    main()
