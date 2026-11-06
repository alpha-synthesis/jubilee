"""Protocols of the reruns, derived from the frozen campaign protocol.

* ``paired_cash.json`` — the frozen confirmatory protocol
  (``outputs/tmlr_revision_20261103/campaign/protocol_frozen.json``) with
  only its name, output directory and ``rewards`` (score and cash) changed.
* ``grid_v2_20seeds.json`` — the seven 20-seed cells of the archived grid on
  generator version 2, seeds 101–120, three candidates, tabular regime only,
  both rewards.
* ``grid_v2_5seeds.json`` — the other ten grid cells, seeds 101–105, same
  settings (five of them have ε = 0: the pilot estimators are undefined there).

Usage::

    python scripts/rerun_20261106/build_protocols.py --out DIR
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FROZEN = "outputs/tmlr_revision_20261103/campaign/protocol_frozen.json"
GRID_20 = ["cell_02_control_eps08", "cell_04_a06_eps08", "cell_06_a10_eps08",
           "cell_08_a14_eps08", "cell_10_a18_eps08", "cell_16_a02_eps08", "cell_17_a04_eps08"]
GRID_5 = ["cell_01_control_eps0", "cell_03_a06_eps0", "cell_05_a10_eps0", "cell_07_a14_eps0",
          "cell_09_a18_eps0", "cell_11_b_noise015", "cell_12_b_noise040", "cell_13_b_noise060",
          "cell_14_corner_14_040", "cell_15_corner_18_060"]


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def paired_cash() -> dict:
    proto = json.loads((REPO / FROZEN).read_text())
    proto["name"] = "paired_rerun_20261106"
    proto["out_dir"] = "outputs/rerun_20261106/paired/runs"
    proto["rewards"] = ["score", "cash"]
    proto["rerun_of"] = {"protocol": FROZEN, "sha256": _sha(REPO / FROZEN),
                         "changed_keys": ["name", "out_dir", "rewards"]}
    return proto


def grid(name: str, cells: list[str], seeds: list[int], out_dir: str, purpose: str) -> dict:
    conds = {c: f"configs/grid/{c}.yaml" for c in cells}
    return {
        "name": name, "purpose": purpose, "out_dir": out_dir,
        "borrowers": 1000000, "batch_size": 50000, "horizon": 9, "logs_months": 12,
        "n_boot": 200, "conditions": conds, "seeds": seeds, "annotator_replicate": 1,
        "reference_replicates": [2, 3, 4], "candidates": ["pi_b", "pi_near", "pi_far"],
        "extra_reference_candidates": [], "annotator": {"bias_frac": 0.25, "noise_frac": 0.25},
        "nontabular": False, "rewards": ["score", "cash"], "selection_z": 1.96,
        "config_sha256": {c: _sha(REPO / p) for c, p in conds.items()},
    }


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    protos = {
        "paired_cash.json": paired_cash(),
        "grid_v2_20seeds.json": grid(
            "grid_v2_20seeds_20261106", GRID_20, list(range(101, 121)),
            "outputs/rerun_20261106/grid20/runs",
            "Archived grid, generator version 2: the seven 20-seed cells (control and the "
            "confounding-strength ladder at eps 0.08), three candidates, tabular regime, "
            "independent reference replicates, score and cash."),
        "grid_v2_5seeds.json": grid(
            "grid_v2_5seeds_20261106", GRID_5, list(range(101, 106)),
            "outputs/rerun_20261106/grid5/runs",
            "Archived grid, generator version 2: the ten 5-seed cells (eps 0 ladder, noise "
            "ladder, corners), three candidates, tabular regime, independent reference "
            "replicates, score and cash; pilot estimators undefined at eps 0."),
    }
    for name, proto in protos.items():
        p = a.out / name
        p.write_text(json.dumps(proto, indent=2) + "\n")
        print(json.dumps({"out": str(p), "sha256": _sha(p), "conditions": len(proto["conditions"]),
                          "seeds": len(proto["seeds"])}))


if __name__ == "__main__":
    main()
