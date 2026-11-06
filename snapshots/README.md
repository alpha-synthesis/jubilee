# Source snapshot of model 2.0.0

The repository root holds simulator model 2.1.0 (full settlement).
`model-2.0.0/` is the source tree of the earlier model 2.0.0 (keyed random
streams, partial payment with continuation), kept so that
`scripts/settlement_equivalence.py` can compare the two models loan by loan.
Its code fingerprint (`scripts/tmlr_campaign.py`, `code_fingerprint`) is
`de3cb466…`, the value recorded in the paired-study runs of
`results/tmlr_revision_20261103/` and in the exploration records. Scripts
that the comparison does not use are not included. It defines the same
packages as the root, so install it in its own environment:

```bash
cd snapshots/model-2.0.0
python3.12 -m venv .venv && . .venv/bin/activate
pip install -r requirements.lock && pip install --no-deps .
```
