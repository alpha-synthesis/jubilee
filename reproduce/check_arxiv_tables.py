"""Rebuild every generated table of the arXiv version of the paper and compare it with the printed one.

Paired-study score tables come from results/tmlr_revision_20261103 (unchanged by the
model-2.1.0 regeneration, whose score panels are identical); grid, cash and DM+ tables
come from results/rerun_20261106. The comparison is byte for byte against
reproduce/expected/arxiv_v1_tables/, which holds the tables printed in the paper.

Usage: python reproduce/check_arxiv_tables.py --work outputs/arxiv_tables
"""
from pathlib import Path
import argparse, subprocess, sys

root = Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser()
ap.add_argument('--work', type=Path, required=True)
a = ap.parse_args()
a.work.mkdir(parents=True, exist_ok=True)
(a.work / 'sections').mkdir(exist_ok=True)
R = root / 'results'
subprocess.run([sys.executable, str(root / 'reproduce/paper/render_campaign_tables.py'),
                '--evidence', str(R / 'tmlr_revision_20261103'),
                '--settlement-evidence', str(R / 'settlement_score_equivalence_20261104'),
                '--exploration-evidence', str(R / 'exploration_effect_20261104'),
                '--rerun-equivalence', str(R / 'rerun_20261106/paired/score_equivalence/summary.json'),
                '--source', str(a.work), '--audit-dir', str(a.work)], check=True)
subprocess.run([sys.executable, str(root / 'reproduce/paper/render_rerun_tables.py'),
                '--rerun', str(R / 'rerun_20261106'), '--source', str(a.work), '--skip-figure'], check=True)
bad = []
expected = sorted((root / 'reproduce/expected/arxiv_v1_tables').glob('*.tex'))
for e in expected:
    g = a.work / ('sections' if e.name == 'campaign_appendix.tex' else 'tables') / e.name
    if not g.exists() or g.read_bytes() != e.read_bytes():
        bad.append(e.name)
print(f'{len(expected) - len(bad)} of {len(expected)} printed tables reproduce byte for byte')
if bad:
    print('differ:', ', '.join(bad)); sys.exit(1)
