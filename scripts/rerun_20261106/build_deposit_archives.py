"""Build the deterministic data-deposit archives of the reruns.

One ZIP per paired-study condition and one per grid protocol, members stored
uncompressed (the parquet files are already zstd-compressed) with a fixed
timestamp and sorted order, so the same inputs give byte-identical archives.
Each archive holds, per run, the cohort extracts and the small run records,
plus the protocol. Writes SHA256SUMS and inventory.csv next to the archives.

Usage (on the server, from the repository root):
  python scripts/rerun_20261106/build_deposit_archives.py \
      --rerun outputs/rerun_20261106 --dest outputs/rerun_20261106/deposit
"""
from pathlib import Path
import argparse, csv, hashlib, zipfile

FIXED = (2026, 11, 6, 0, 0, 0)
MEMBERS = ("logs.parquet", "annotator.parquet", "logs_meta.json", "annotator_meta.json",
           "reference_r2.json", "reference_r3.json", "reference_r4.json", "panel.json", "panel_cash.json")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def write_zip(dest: Path, files: list[tuple[str, Path]], inventory: list[dict]) -> None:
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as z:
        for arc, src in sorted(files):
            info = zipfile.ZipInfo(arc, date_time=FIXED)
            info.external_attr = 0o644 << 16
            with src.open("rb") as fi, z.open(info, "w", force_zip64=True) as fo:
                while chunk := fi.read(1 << 22):
                    fo.write(chunk)
            inventory.append({"archive": dest.name, "member": arc, "bytes": src.stat().st_size,
                              "sha256": sha256(src)})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rerun", type=Path, required=True)
    ap.add_argument("--dest", type=Path, required=True)
    a = ap.parse_args()
    a.dest.mkdir(parents=True, exist_ok=True)
    inventory = []
    groups = []
    for cond in ("A_off", "A_on", "B_off", "B_on"):
        groups.append((f"jubilee-paired-rerun-extracts-{cond}.zip", "paired", [cond]))
    groups.append(("jubilee-grid-v2-extracts-20seed.zip", "grid20", None))
    groups.append(("jubilee-grid-v2-extracts-5seed.zip", "grid5", None))
    for name, proto, conds in groups:
        root = a.rerun / proto
        runs = sorted(p for p in (root / "runs").glob("*/seed*") if p.is_dir())
        if conds is not None:
            runs = [r for r in runs if r.parent.name in conds]
        files = [(f"rerun_20261106/{proto}/protocol.json", root / "protocol.json")]
        for r in runs:
            for m in MEMBERS:
                p = r / m
                if p.exists():
                    files.append((f"rerun_20261106/{proto}/runs/{r.parent.name}/{r.name}/{m}", p))
        write_zip(a.dest / name, files, inventory)
        print(name, len(runs), "runs", sum(f[1].stat().st_size for f in files) / 1e9, "GB")
    with (a.dest / "inventory.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["archive", "member", "bytes", "sha256"])
        w.writeheader(); w.writerows(inventory)
    sums = [f"{sha256(p)}  {p.name}" for p in sorted(a.dest.glob("*.zip"))]
    (a.dest / "SHA256SUMS").write_text("\n".join(sums) + "\n")
    print("\n".join(sums))


if __name__ == "__main__":
    main()
