"""Freeze the confirmatory protocol: add hashes, refuse to overwrite.

Takes a draft protocol JSON (the driver's format) and writes
``protocol_frozen.json`` with the sha256 of every condition config, of the
pre-registered rule files and of the pilot report, the code fingerprint, and
the freeze time. A frozen file is never overwritten; a change needs a new,
dated file.

Usage::

    python scripts/tmlr_evidence/freeze_protocol.py --draft DRAFT.json \
        --attach precision_rule.md gbm_selection_rule.md pilot_report.md pilot_sizing.json \
        --out protocol_frozen.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from tmlr_campaign import code_fingerprint  # noqa: E402


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--draft", type=Path, required=True)
    ap.add_argument("--attach", nargs="*", type=Path, default=[])
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.out.exists():
        raise SystemExit(f"{a.out} exists: a frozen protocol is never overwritten")
    proto = json.loads(a.draft.read_text())
    proto["frozen_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    proto["config_sha256"] = {c: _sha(REPO / p) for c, p in proto["conditions"].items()}
    proto["attached_sha256"] = {str(p): _sha(p) for p in a.attach}
    proto["code_fingerprint_at_freeze"] = code_fingerprint()
    a.out.write_text(json.dumps(proto, indent=2))
    print(json.dumps({"out": str(a.out), "sha256": _sha(a.out),
                      "code": proto["code_fingerprint_at_freeze"]["tree_sha256"]}))


if __name__ == "__main__":
    main()
