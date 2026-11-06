"""Shared fixtures for the OPE test suite."""

from __future__ import annotations

import pytest


@pytest.fixture
def record_metric(request):
    """Return ``rec(**metrics)`` — echoes this test's headline metrics.

    The metrics are printed with ``-s``.
    """

    def _rec(**kwargs):
        vals = ", ".join(f"{k}={float(v):.4f}" for k, v in kwargs.items())
        print(f"[metric] {request.node.name}: {vals}")

    return _rec
