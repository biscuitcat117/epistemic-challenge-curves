"""Build the frozen four-model controlled-odds panel analysis."""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from itertools import combinations
from pathlib import Path
from statistics import mean
from typing import Any

from analyze_results import (
    TAG_FIELDS,
    challenge_curve,
    duplicate_response_stats,
    empirical_crossing,
    grader_curves,
    grouped,
    load_consensus,
    load_jsonl,
    quantile,
    scenario_thresholds,
    tag_rates,
    wilson_interval,
)


ROOT = Path(__file__).resolve().parent
HOLDOUT_SCORING = ROOT / "outputs" / "module_a_holdout_v0_1" / "scoring"
EXTENSION_SCORING = ROOT / "outputs" / "module_a_model_extension_v0_1" / "scoring"
DEFAULT_OUTPUT = (
    ROOT / "outputs" / "module_a_model_extension_v0_1" / "panel_analysis.json"
)

CLAUDE = "openrouter/anthropic/claude-sonnet-5"
GPT = "openrouter/openai/gpt-5.6-terra"
GROK = "openrouter/x-ai/grok-4.5"
GLM = "openrouter/z-ai/glm-5.2"
MODEL_ORDER = (CLAUDE, GPT, GROK, GLM)
MODEL_LABELS = {
    CLAUDE: "Claude Sonnet 5",
    GPT: "GPT-5.6 Terra",
    GROK: "Grok 4.5",
    GLM: "GLM 5.2",
}


def interval(values: list[float]) -> list[float] | None:
    if not values:
        return None
    return [quantile(values, 0.025), quantile(values, 0.975)]


def _validate_rows(
    rows: list[dict[str, Any]], expected_models: set[str], source: str
) -> None:
    models = {str(row["target_model"]) for row in rows}
    if models != expected_models:
        raise ValueError(f"{source} models are {sorted(models)}, expected {sorted(expected_models)}")
    cell_sizes = Counter(
        (str(row["target_model"]), str(row["prompt_id"])) for row in rows
    )
    if set(cell_sizes.values()) != {5}:
        raise ValueError(f"{source} does not have five responses in every model-prompt cell")
    expected_rows = len(expected_models) * 36 * 5
    if len(rows) != expected_rows:
        raise ValueError(f"{source} has {len(rows)} responses, expected {expected_rows}")


def model_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    curve = challenge_curve(rows)
    scenarios = scenario_thresholds(rows)
    any_count = sum(int(row["any_challenge"]) for row in rows)
    soft_count = sum(int(row["challenge_level"]) == 1 for row in rows)
    explicit_count = sum(int(row["explicit_challenge"]) for row in rows)
    reversal_values = [float(row["reversal_mass"]) for row in scenarios]
    return {
        "n": len(rows),
        "overall_any_challenge_count": any_count,
        "overall_any_challenge_rate": any_count / len(rows),
        "overall_any_challenge_wilson_95": wilson_interval(any_count, len(rows)),
        "overall_soft_challenge_count": soft_count,
        "overall_soft_challenge_rate": soft_count / len(rows),
        "overall_explicit_challenge_count": explicit_count,
        "overall_explicit_challenge_rate": explicit_count / len(rows),
        "empirical_s50_log10": empirical_crossing(curve),
        "curve": curve,
        "scenario_thresholds": scenarios,
        "monotonic_scenario_count": sum(bool(row["monotonic"]) for row in scenarios),
        "nonmonotonic_scenario_count": sum(
            not bool(row["monotonic"]) for row in scenarios
        ),
        "mean_reversal_mass": mean(reversal_values),
        "total_reversal_mass": sum(reversal_values),
        "largest_adjacent_reversal": max(
            float(row["largest_adjacent_reversal"]) for row in scenarios
        ),
        "tag_rates": tag_rates(rows),
        "agreement": dict(Counter(str(row["level_agreement"]) for row in rows)),
        "duplicate_responses": duplicate_response_stats(rows),
    }


def pairwise_bootstrap(
    rows: list[dict[str, Any]], iterations: int = 10_000, seed: int = 20_260_715
) -> dict[str, Any]:
    model_rows = grouped(rows, "target_model")
    scenarios = sorted({str(row["scenario_id"]) for row in rows})
    if len(scenarios) != 6:
        raise ValueError(f"Expected six paired scenarios, found {len(scenarios)}")
    by_model_scenario = {
        model: grouped(values, "scenario_id") for model, values in model_rows.items()
    }
    rng = random.Random(seed)
    samples = [[rng.choice(scenarios) for _ in scenarios] for _ in range(iterations)]
    output: dict[str, Any] = {}

    for left, right in combinations(MODEL_ORDER, 2):
        challenge_differences: list[float] = []
        s50_differences: list[float] = []
        for sampled_scenarios in samples:
            left_rows = [
                row
                for scenario in sampled_scenarios
                for row in by_model_scenario[left][scenario]
            ]
            right_rows = [
                row
                for scenario in sampled_scenarios
                for row in by_model_scenario[right][scenario]
            ]
            challenge_differences.append(
                mean(int(row["any_challenge"]) for row in left_rows)
                - mean(int(row["any_challenge"]) for row in right_rows)
            )
            left_s50 = empirical_crossing(challenge_curve(left_rows))
            right_s50 = empirical_crossing(challenge_curve(right_rows))
            if left_s50 is not None and right_s50 is not None:
                s50_differences.append(float(left_s50 - right_s50))

        key = f"{left}__minus__{right}"
        output[key] = {
            "left_model": left,
            "right_model": right,
            "left_label": MODEL_LABELS[left],
            "right_label": MODEL_LABELS[right],
            "overall_challenge_rate_left_minus_right": {
                "percentile_95_interval": interval(challenge_differences),
                "share_above_zero": mean(value > 0 for value in challenge_differences),
            },
            "empirical_s50_left_minus_right": {
                "valid_resamples": len(s50_differences),
                "percentile_95_interval": interval(s50_differences),
                "share_above_zero": (
                    mean(value > 0 for value in s50_differences)
                    if s50_differences
                    else None
                ),
            },
        }
    return {
        "iterations": iterations,
        "seed": seed,
        "resampling_unit": "scenario family, paired across all four target models",
        "comparisons": output,
    }


def grader_sensitivity_summary(
    consensus_rows: list[dict[str, Any]], grader_rows: list[dict[str, Any]], models: dict[str, Any]
) -> dict[str, Any]:
    curves = grader_curves(consensus_rows, grader_rows)
    s50: dict[str, dict[str, int | None]] = {}
    maximum_deviation = 0.0
    for model, grader_values in curves.items():
        s50[model] = {}
        consensus = {
            int(point["level"]): float(point["any_challenge_rate"])
            for point in models[model]["curve"]
        }
        for grader, points in grader_values.items():
            s50[model][grader] = empirical_crossing(points)
            for point in points:
                maximum_deviation = max(
                    maximum_deviation,
                    abs(
                        float(point["any_challenge_rate"])
                        - consensus[int(point["level"])]
                    ),
                )
    return {
        "curves": curves,
        "empirical_s50_log10": s50,
        "maximum_absolute_curve_deviation": maximum_deviation,
    }


def build_panel(
    holdout_rows: list[dict[str, Any]],
    extension_rows: list[dict[str, Any]],
    holdout_graders: list[dict[str, Any]],
    extension_graders: list[dict[str, Any]],
) -> dict[str, Any]:
    _validate_rows(holdout_rows, {CLAUDE, GPT}, "holdout")
    _validate_rows(extension_rows, {GROK, GLM}, "extension")
    rows = holdout_rows + extension_rows
    graders = holdout_graders + extension_graders
    models = {
        model: model_summary(
            [row for row in rows if str(row["target_model"]) == model]
        )
        for model in MODEL_ORDER
    }
    ranking = sorted(
        MODEL_ORDER,
        key=lambda model: (
            models[model]["empirical_s50_log10"] is None,
            models[model]["empirical_s50_log10"]
            if models[model]["empirical_s50_log10"] is not None
            else float("inf"),
            -models[model]["overall_any_challenge_rate"],
        ),
    )
    return {
        "analysis_role": "pre-specified descriptive model extension",
        "criteria_source": "MODEL_EXTENSION_PLAN.md",
        "counts": {
            "panel_target_responses": len(rows),
            "existing_holdout_responses": len(holdout_rows),
            "new_extension_responses": len(extension_rows),
            "grader_labels": len(graders),
            "target_models": len(MODEL_ORDER),
            "scenario_families": len({str(row["scenario_id"]) for row in rows}),
            "levels_per_scenario": len({int(row["level"]) for row in rows}),
            "replicates_per_cell": [5],
        },
        "model_order": list(MODEL_ORDER),
        "model_labels": MODEL_LABELS,
        "models": models,
        "descriptive_ranking_earliest_s50": ranking,
        "pairwise_scenario_cluster_bootstrap": pairwise_bootstrap(rows),
        "grader_sensitivity": grader_sensitivity_summary(rows, graders, models),
        "limitations": [
            "Model selection followed inspection of the Claude/GPT holdout results.",
            "Grok uses mandatory low reasoning while the other panel targets use disabled hidden reasoning.",
            "The six controlled-odds scenario families do not represent every testimony domain.",
            "Automated ensemble labels remain judge-sensitive and are not human annotations.",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--holdout-scoring", type=Path, default=HOLDOUT_SCORING)
    parser.add_argument("--extension-scoring", type=Path, default=EXTENSION_SCORING)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    holdout_rows = load_consensus(args.holdout_scoring / "consensus_labels.csv")
    extension_rows = load_consensus(args.extension_scoring / "consensus_labels.csv")
    holdout_graders = load_jsonl(args.holdout_scoring / "grader_labels.jsonl")
    extension_graders = load_jsonl(args.extension_scoring / "grader_labels.jsonl")
    output = build_panel(
        holdout_rows, extension_rows, holdout_graders, extension_graders
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(args.output.resolve())


if __name__ == "__main__":
    main()
