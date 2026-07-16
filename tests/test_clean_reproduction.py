from __future__ import annotations

import json
from pathlib import Path

from epistemic_challenge_curves.analysis import (
    CLAUDE,
    GLM,
    GPT,
    GROK,
    build_results,
    read_consensus,
    wilson_interval,
)
from epistemic_challenge_curves.reproduce import reproduce


ROOT = Path(__file__).resolve().parents[1]
HOLDOUT = (
    ROOT
    / "data"
    / "holdout"
    / "consensus_labels.csv"
)
EXTENSION = (
    ROOT
    / "data"
    / "model_extension"
    / "consensus_labels.csv"
)


def test_clean_analysis_reproduces_saved_panel() -> None:
    clean = build_results(HOLDOUT, EXTENSION)

    expected = {
        CLAUDE: (139, 2, [4, 15, 30, 30, 30, 30]),
        GPT: (20, 10, [0, 0, 1, 1, 2, 16]),
        GROK: (24, None, [1, 1, 2, 4, 7, 9]),
        GLM: (59, 8, [2, 5, 11, 9, 17, 15]),
    }
    for model, (count, s50, curve_counts) in expected.items():
        summary = clean["models"][model]
        assert summary["any_challenge_count"] == count
        assert summary["empirical_s50_log10"] == s50
        assert [point["any_challenge_count"] for point in summary["challenge_curve"]] == curve_counts
        assert len(summary["any_challenge_wilson_95"]) == 2
        assert all(
            len(point["any_challenge_wilson_95"]) == 2
            for point in summary["challenge_curve"]
        )

    comparisons = clean["pairwise_scenario_cluster_bootstrap"]["comparisons"]
    expected_intervals = {
        f"{CLAUDE}__minus__{GPT}": [0.5611111111111111, 0.7611111111111112],
        f"{CLAUDE}__minus__{GROK}": [0.5333333333333333, 0.7388888888888889],
        f"{CLAUDE}__minus__{GLM}": [0.32777777777777783, 0.5666666666666667],
        f"{GPT}__minus__{GROK}": [-0.12222222222222222, 0.0611111111111111],
        f"{GPT}__minus__{GLM}": [-0.3222222222222222, -0.10555555555555557],
        f"{GROK}__minus__{GLM}": [-0.3055555555555556, -0.09444444444444441],
    }
    assert {
        key: value["overall_challenge_rate_left_minus_right"][
            "percentile_95_interval"
        ]
        for key, value in comparisons.items()
    } == expected_intervals
    assert clean["clean_holdout_comparison"]["paired_family_bootstrap"][
        "percentile_95_interval"
    ] == [0.5611111111111111, 0.7611111111111112]
    assert all(
        not value.startswith("/") for value in clean["source_data"].values()
    )


def test_one_command_reproduction_writes_public_artifacts(tmp_path: Path) -> None:
    paths = reproduce(HOLDOUT, EXTENSION, tmp_path)
    assert {path.name for path in paths} == {
        "summary.json",
        "table_4_model_summary.csv",
        "table_5_holdout_behaviors.csv",
        "figure_1_challenge_curves.svg",
    }
    assert all(path.is_file() and path.stat().st_size > 0 for path in paths)
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert all(
        "any_challenge_wilson_95" in point
        for model in summary["models"].values()
        for point in model["challenge_curve"]
    )


def test_wilson_interval_validates_inputs_and_matches_reference_value() -> None:
    lower, upper = wilson_interval(15, 30)
    assert round(lower, 6) == 0.331541
    assert round(upper, 6) == 0.668459

    for successes, total in ((-1, 30), (31, 30), (0, 0)):
        try:
            wilson_interval(successes, total)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid Wilson-interval input was accepted")


def test_public_data_contains_each_study_phase_once() -> None:
    expected_counts = {
        "pilot": 72,
        "replication": 144,
        "holdout": 360,
        "model_extension": 360,
    }
    total = 0
    for phase, expected in expected_counts.items():
        rows = read_consensus(ROOT / "data" / phase / "consensus_labels.csv")
        assert len(rows) == expected
        keys = {
            (
                row["target_model"],
                row["prompt_id"],
                int(row.get("replicate") or 1),
            )
            for row in rows
        }
        assert len(keys) == expected
        total += len(rows)
    assert total == 936


def test_prompt_inventories_have_documented_scope() -> None:
    def read_jsonl(path: Path) -> list[dict[str, object]]:
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    development = read_jsonl(ROOT / "data" / "prompts" / "development.jsonl")
    holdout = read_jsonl(ROOT / "data" / "prompts" / "holdout.jsonl")
    assert len(development) == 52
    assert sum(row["module"] == "A_controlled" for row in development) == 36
    assert sum(row["module"] == "B_implicit" for row in development) == 16
    assert len(holdout) == 36
    assert {row["module"] for row in holdout} == {"A_holdout"}
