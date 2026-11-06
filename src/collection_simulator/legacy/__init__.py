"""Executable source snapshots of earlier simulator models (not runtime options).

* ``generator_2_0_0`` — byte-identical copy of ``collection_simulator/generator.py``
  at model version 2.0.0 (random-stream scheme ``keyed-streams-v2``), taken
  before the full-settlement correction of model 2.1.0. Under 2.0.0 a
  recovering borrower paid ``settlement × min(1, 0.7 + Beta(2, 5))``, the
  payment was subtracted from the balance and the loan returned to
  ``performing`` unless the balance fell below ``max(50, 0.05 × principal)``.
  It produced the paired-study campaign and its auxiliary analyses. Its
  sha256 is recorded in
  ``outputs/settlement_score_equivalence_20261104`` (the copy is unchanged, so
  the module docstring still describes itself as the current generator).

Import it explicitly (``from collection_simulator.legacy import
generator_2_0_0``) to reproduce 2.0.0 trajectories; :func:`collection_simulator.generate`
and :func:`collection_simulator.generator.simulate_cohort` always run the
current model. The snapshot shares ``dictionaries`` and ``storage`` with the
current package. Generator version 1 (single random stream, archived 190-run
grid) is preserved in the repository history, not here.
"""
