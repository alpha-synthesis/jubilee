"""Shared fixtures for the OPE test suite."""

from __future__ import annotations

import pytest


@pytest.fixture
def record_metric(request):
    """Return ``rec(**metrics)`` — echoes this test's headline metrics.

    (In the internal suite this fed a model-validation report; here the
    metrics are simply printed with ``-s`` so a reviewer can inspect them.)
    """

    def _rec(**kwargs):
        vals = ", ".join(f"{k}={float(v):.4f}" for k, v in kwargs.items())
        print(f"[metric] {request.node.name}: {vals}")

    return _rec
