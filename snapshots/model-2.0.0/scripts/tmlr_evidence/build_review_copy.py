"""Assemble an anonymised copy of the revision materials for double-blind review.

Copies (never moves) the repository content that git lists, minus files that
are internal by nature (``--exclude``), plus the given result directories,
then sweeps every text file of the copy for identifying strings read from a
local file (``--banned``, one regular expression per line; the list itself is
never copied). Parquet files are swept by their decoded contents (column
names, string values, file metadata), not by their compressed bytes; other
binary files by their bytes read as latin-1. Files named in ``--sanitize``
(e.g. ``.gitignore``) are copied without the lines that match a banned
pattern; the dropped line numbers are recorded. In the copied result files,
the values of the JSON keys named in ``--redact-keys`` (e.g. version-control
commit identifiers) are replaced by ``redacted-for-review`` when they are
hexadecimal; the number of values replaced per file and the distinct originals
are recorded. The sweep report (which names the patterns hit) is written next
to the copy, never inside it
(``--report``, default ``<dest>_anonymity_sweep.json``). The internal
originals are left untouched.

Usage::

    python scripts/tmlr_evidence/build_review_copy.py --dest DIR --banned LIST \
        --results outputs/.../tables outputs/.../protocol_frozen.json \
        --exclude internal_notes.md --sanitize .gitignore --redact-keys git_head
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _parquet_text(path: Path) -> str:
    """Column names, distinct string values and key-value metadata of a
    parquet file, one item per line (read with duckdb, a core dependency)."""
    import duckdb

    con = duckdb.connect()
    try:
        rel = con.execute(f"SELECT * FROM read_parquet('{path}') LIMIT 0")
        cols = [d[0] for d in rel.description]
        types = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{path}')").fetchall()
        items = list(cols)
        for name, typ, *_ in types:
            if typ.upper() in ("VARCHAR", "STRING") or typ.upper().startswith("ENUM"):
                items += [str(v[0]) for v in con.execute(
                    f'SELECT DISTINCT "{name}" FROM read_parquet(\'{path}\')').fetchall()]
        items += [f"{k!r}={v!r}" for k, v in con.execute(
            f"SELECT key, value FROM parquet_kv_metadata('{path}')").fetchall()]
    finally:
        con.close()
    return "\n".join(items)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dest", type=Path, required=True)
    ap.add_argument("--banned", type=Path, required=True)
    ap.add_argument("--results", nargs="*", type=Path, default=[])
    ap.add_argument("--exclude", nargs="*", default=[])
    ap.add_argument("--exclude-prefix", nargs="*", default=[])
    ap.add_argument("--sanitize", nargs="*", default=[])
    ap.add_argument("--report", type=Path, default=None)
    ap.add_argument("--redact-keys", nargs="*", default=[])
    a = ap.parse_args(argv)
    report_path = a.report or a.dest.with_name(a.dest.name + "_anonymity_sweep.json")
    if report_path.resolve().is_relative_to(a.dest.resolve()):
        raise SystemExit("--report must lie outside --dest")
    if a.dest.exists() and any(a.dest.iterdir()):
        raise SystemExit(f"{a.dest} is not empty; choose a new directory")
    patterns = [re.compile(line.strip(), re.IGNORECASE)
                for line in a.banned.read_text().splitlines()
                if line.strip() and not line.startswith("#")]
    sanitized = {}
    listed = subprocess.run(["git", "-C", str(REPO), "ls-files", "--cached", "--others",
                             "--exclude-standard"], capture_output=True, text=True,
                            check=True).stdout.splitlines()
    copied = []
    for rel in sorted(set(listed)):
        if rel in a.exclude or any(rel.startswith(p) for p in a.exclude_prefix):
            continue
        src = REPO / rel
        if not src.is_file():
            continue
        tgt = a.dest / "code" / rel
        tgt.parent.mkdir(parents=True, exist_ok=True)
        if rel in a.sanitize:
            lines = src.read_text().splitlines()
            dropped = [i for i, ln in enumerate(lines, 1) if any(p.search(ln) for p in patterns)]
            tgt.write_text("\n".join(ln for i, ln in enumerate(lines, 1) if i not in dropped)
                           + "\n")
            sanitized[rel] = dropped
        else:
            shutil.copy2(src, tgt)
        copied.append(f"code/{rel}")
    for res in a.results:
        res = res if res.is_absolute() else REPO / res
        tgt = a.dest / "results" / res.name
        if res.is_dir():
            shutil.copytree(res, tgt)
            copied += [str(p.relative_to(a.dest)) for p in sorted(tgt.rglob("*")) if p.is_file()]
        else:
            tgt.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(res, tgt)
            copied.append(str(tgt.relative_to(a.dest)))
    redacted, originals = {}, set()
    if a.redact_keys:
        keys = "|".join(re.escape(k) for k in a.redact_keys)
        value = re.compile(rf'("(?:{keys})"\s*:\s*")([0-9a-fA-F]{{7,64}})(")')
        for rel in copied:
            p = a.dest / rel
            if not rel.startswith("results/") or p.suffix not in (".json", ".jsonl"):
                continue
            text = p.read_text()
            found = value.findall(text)
            if found:
                originals.update(v for _, v, _ in found)
                p.write_text(value.sub(r"\1redacted-for-review\3", text))
                redacted[rel] = len(found)
    hits = []
    for rel in copied:
        p = a.dest / rel
        if p.suffix == ".parquet":
            text = _parquet_text(p)
        else:
            try:
                text = p.read_text()
            except UnicodeDecodeError:
                text = p.read_bytes().decode("latin-1")
        for i, line in enumerate(text.splitlines(), 1):
            for pat in patterns:
                if pat.search(line) or pat.search(rel):
                    hits.append({"file": rel, "line": i, "pattern": pat.pattern})
    manifest = {rel: hashlib.sha256((a.dest / rel).read_bytes()).hexdigest() for rel in copied}
    report = {"files": len(copied), "excluded": a.exclude + a.exclude_prefix,
              "sanitized_lines_dropped": sanitized,
              "redacted_keys": a.redact_keys, "redacted_values_per_file": redacted,
              "redacted_originals": sorted(originals),
              "banned_patterns": len(patterns), "hits": hits}
    (a.dest / "review_copy_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True))
    report_path.write_text(json.dumps(report, indent=2))
    print(json.dumps({"files": len(copied), "hits": len(hits)}))


if __name__ == "__main__":
    main()
