"""Command line interface."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from collection_simulator.config import load_config
from collection_simulator.export import export_csv, read_seed, sample_subpath
from collection_simulator.generator import generate
from collection_simulator.validation import validate_database


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="collection-simulator")
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate")
    gen.add_argument("--config", required=True)
    gen.add_argument("--out", required=True)
    gen.add_argument("--seed", type=int, help="Override the YAML seed for this run")
    gen.add_argument(
        "--batch-size",
        type=int,
        help="Stream generation in borrower batches of this size (memory-bounded); "
        "needed for very large populations. Omit to generate in one shot.",
    )

    exp = sub.add_parser("export")
    exp.add_argument("--db", required=True)
    exp.add_argument("--out")
    exp.add_argument("--mode", choices=["split", "flat", "both"], default="split")
    exp.add_argument("--all", action="store_true", help="shorthand for --mode both")
    exp.add_argument(
        "--scenario",
        help="label; when set (or with --s3), files go under the structured layout "
        "collection-simulator/samples/<scenario>/<date>/seed<seed>-<HHMMSS>/",
    )
    exp.add_argument("--s3", help="s3://bucket[/prefix] to also upload the exported files to")
    exp.add_argument("--profile", help="AWS profile name for the upload")
    exp.add_argument("--region", default="us-east-1", help="AWS region (default us-east-1)")

    val = sub.add_parser("validate")
    val.add_argument("--db", required=True)

    orl = sub.add_parser(
        "oracleless-report",
        help="public-data diagnostics only (no oracle_truth): distribution, overlap, "
        "model-free assignment dependence, and ε-floor exploration coverage",
    )
    orl.add_argument("--db", required=True)
    orl.add_argument("--config", required=True)
    orl.add_argument("--out", default="outputs/oracleless_report.md")
    orl.add_argument("--no-figures", action="store_true")

    ope = sub.add_parser(
        "ope-eval",
        help="grade an external OPE policy CSV against the simulator oracle "
        "(five analyses + figures + markdown report)",
    )
    ope.add_argument("--db", required=True, help="sim.duckdb with oracle_truth")
    ope.add_argument("--policy", required=True, help="policy CSV (loan_id,month,channel,discount_offer,p_payment,…)")
    ope.add_argument("--config", required=True, help="the YAML config the data was generated with")
    ope.add_argument("--out", default="outputs/ope_evaluation_report.md")
    ope.add_argument("--no-figures", action="store_true", help="skip matplotlib figures")

    args = parser.parse_args(argv)
    if args.command == "generate":
        cfg = load_config(args.config)
        if args.seed is not None:
            cfg["seed"] = args.seed
        result = generate(cfg, args.out, batch_size=args.batch_size)
        report = validate_database(result.db_path)
        print(
            json.dumps(
                {"db": str(result.db_path), "seed": cfg["seed"], "counts": report.counts},
                indent=2,
            )
        )
        return 0 if report.ok else 2
    if args.command == "export":
        # Structured sample layout when a scenario is named or we're uploading;
        # otherwise legacy behaviour (write straight into --out or <db>/csv).
        structured = args.scenario is not None or args.s3 is not None
        subpath = None
        if structured:
            seed = read_seed(args.db)
            scenario = args.scenario or "unspecified"
            subpath = sample_subpath(scenario, seed, datetime.now(timezone.utc))
            base = Path(args.out) if args.out else Path(args.db).resolve().parent
            out_dir = base / subpath
        else:
            out_dir = args.out
        mode = "both" if args.all else args.mode
        paths = export_csv(args.db, out_dir, mode)
        result = {"files": [str(Path(p)) for p in paths]}
        if args.s3:
            from collection_simulator.s3 import parse_s3_uri, upload_files

            bucket, base_prefix = parse_s3_uri(args.s3)
            key_prefix = f"{base_prefix}/{subpath}".strip("/") if base_prefix else subpath
            result["uploaded"] = upload_files(
                paths, bucket, key_prefix, profile=args.profile, region=args.region
            )
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "ope-eval":
        from collection_simulator.ope_eval import evaluate_ope

        metrics = evaluate_ope(
            args.db, args.policy, args.config, out_path=args.out,
            make_figures=not args.no_figures,
        )
        pv = metrics["policy_value"]
        policies = ["realized", "pi_b_logged", "pi_e_policy", "pi_star_ceiling"]
        print(json.dumps({
            "report": metrics["report_path"],
            "rows": metrics["n_rows"],
            "recovery_rate": {k: pv[k]["recovery_rate"] for k in policies},
            "money": {k: pv[k]["money"] for k in policies},
            "money_optimal_discount_mean": round(pv["money_optimal_discount_mean"], 3),
            "calibration_optimism_x": round(metrics["calibration"]["optimism_x"], 2),
            "zero_discount_optimal_d": metrics["zero_discount"]["oracle_optimal_discount"],
            "zero_discount_uplift_pct": round(metrics["zero_discount"]["uplift_pct"], 1),
        }, indent=2))
        return 0

    if args.command == "oracleless-report":
        from collection_simulator.oracleless_report import evaluate_oracleless

        m = evaluate_oracleless(args.db, args.config, out_path=args.out, make_figures=not args.no_figures)
        print(json.dumps({
            "report": m["report_path"], "rows": m["n_rows"],
            "recovery_rate": round(m["recovery_rate"], 5),
            "assignment_dependence": round(m["assignment_dependence"], 4),
            "min_stratum_action_share": round(m["min_stratum_action_share"], 4),
            "exploration_share_active": round(m["exploration"].get("share_in_active", 0.0), 4),
        }, indent=2))
        return 0

    if args.command == "validate":
        report = validate_database(args.db)
        print(
            json.dumps(
                {"ok": report.ok, "counts": report.counts, "errors": report.errors},
                indent=2,
            )
        )
        return 0 if report.ok else 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
