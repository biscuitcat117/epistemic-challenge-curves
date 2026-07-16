from __future__ import annotations

from analyze_model_panel import interval


def test_interval_uses_frozen_percentile_bounds() -> None:
    values = [float(value) for value in range(101)]
    assert interval(values) == [2.5, 97.5]


def test_interval_handles_no_valid_s50_resamples() -> None:
    assert interval([]) is None
