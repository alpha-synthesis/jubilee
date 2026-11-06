"""Compare the rerun's score panels (model 2.1.0) with the archived 2.0.0 panels, field by field.

The score-equivalence argument predicts identical estimator inputs, so every
numeric field under the estimation blocks should agree. Numeric leaves are
compared exactly and with a relative tolerance; provenance, code, environment
and timing fields are excluded because they describe the run, not its result.

Usage:
  python scripts/rerun_20261106/compare_paired_score.py \
      --archived outputs/tmlr_revision_20261103/campaign/runs \
      --rerun outputs/rerun_20261106/paired/runs --out outputs/rerun_20261106/paired/score_equivalence
"""
from pathlib import Path
import argparse, csv, json, math

SKIP = {"protocol", "protocol_sha256", "simulation_provenance", "code", "environment", "timing",
        "seconds", "wall_seconds", "reward", "reward_definition", "reward_column", "elapsed",
        "estimate_seconds"}


def leaves(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in SKIP:
                continue
            yield from leaves(v, f"{prefix}/{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from leaves(v, f"{prefix}[{i}]")
    else:
        yield prefix, obj


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--archived", type=Path, required=True)
    ap.add_argument("--rerun", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--rtol", type=float, default=1e-9)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    per_run, diffs = [], []
    for old in sorted(a.archived.glob("*/seed*/panel.json")):
        cond, seed = old.parent.parent.name, old.parent.name
        new = a.rerun / cond / seed / "panel.json"
        if not new.exists():
            per_run.append({"cond": cond, "seed": seed, "status": "missing"}); continue
        A = dict(leaves(json.loads(old.read_text())))
        B = dict(leaves(json.loads(new.read_text())))
        keys = sorted(set(A) & set(B))
        n_eq = n_close = n_diff = 0
        for k in keys:
            x, y = A[k], B[k]
            if x == y or (isinstance(x, float) and isinstance(y, float) and math.isnan(x) and math.isnan(y)):
                n_eq += 1
            elif isinstance(x, (int, float)) and isinstance(y, (int, float)) and not isinstance(x, bool) \
                    and abs(x - y) <= a.rtol * max(1.0, abs(x), abs(y)):
                n_close += 1
            else:
                n_diff += 1
                diffs.append({"cond": cond, "seed": seed, "field": k, "archived": x, "rerun": y})
        per_run.append({"cond": cond, "seed": seed, "status": "compared", "fields_common": len(keys),
                        "equal": n_eq, "within_rtol": n_close, "different": n_diff,
                        "only_archived": len(set(A) - set(B)), "only_rerun": len(set(B) - set(A))})
    with (a.out / "per_run.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["cond", "seed", "status", "fields_common", "equal", "within_rtol",
                                          "different", "only_archived", "only_rerun"])
        w.writeheader(); w.writerows(per_run)
    with (a.out / "differences.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["cond", "seed", "field", "archived", "rerun"])
        w.writeheader(); w.writerows(diffs)
    done = [r for r in per_run if r["status"] == "compared"]
    summary = {"runs_compared": len(done), "runs_missing": len(per_run) - len(done),
               "fields_compared": sum(r["fields_common"] for r in done),
               "fields_equal": sum(r["equal"] for r in done),
               "fields_within_rtol": sum(r["within_rtol"] for r in done),
               "fields_different": sum(r["different"] for r in done),
               "runs_identical": sum(1 for r in done if r["different"] == 0 and r["within_rtol"] == 0),
               "rtol": a.rtol}
    (a.out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
