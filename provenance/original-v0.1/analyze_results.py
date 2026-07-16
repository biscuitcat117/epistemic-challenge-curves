"""Summarize automated Epistemic Challenge Curve labels for reporting."""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT_DIR = ROOT / "outputs" / "automated_scoring_v0_1"
DEFAULT_OUTPUT = DEFAULT_INPUT_DIR / "analysis_summary.json"
TAG_FIELDS = (
    "rarity_acknowledged",
    "conditional_language",
    "alternative_explanation",
    "safety_or_task_bypass",
    "accusatory",
)


def wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> list[float]:
    """Return a two-sided Wilson score interval for a binomial proportion."""

    if total < 1:
        raise ValueError("total must be positive")
    proportion = successes / total
    denominator = 1 + z * z / total
    centre = (proportion + z * z / (2 * total)) / denominator
    radius = (
        z
        * math.sqrt(
            proportion * (1 - proportion) / total + z * z / (4 * total * total)
        )
        / denominator
    )
    return [max(0.0, centre - radius), min(1.0, centre + radius)]


def load_consensus(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    integer_fields = (
        "level",
        "repetitions",
        "surprisal_log10",
        "challenge_level",
        "any_challenge",
        "explicit_challenge",
        *TAG_FIELDS,
    )
    for row in rows:
        for field in integer_fields:
            row[field] = int(row[field])
        row["replicate"] = int(row.get("replicate") or 1)
        row["phase"] = str(row.get("phase") or "pilot")
        row["response_id"] = str(
            row.get("response_id") or f"{row['prompt_id']}::r{row['replicate']}"
        )
        row["grader_levels"] = json.loads(row["grader_levels"])
    return rows


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def grouped(rows: Iterable[dict[str, Any]], field: str) -> dict[str, list[dict[str, Any]]]:
    output: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        output[str(row[field])].append(row)
    return dict(output)


def challenge_curve(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    for level, level_rows in sorted(
        ((int(level), values) for level, values in grouped(rows, "level").items())
    ):
        successes = sum(int(row["any_challenge"]) for row in level_rows)
        explicit = sum(int(row["explicit_challenge"]) for row in level_rows)
        points.append(
            {
                "level": level,
                "surprisal_log10": int(level_rows[0]["surprisal_log10"]),
                "n": len(level_rows),
                "any_challenge_count": successes,
                "any_challenge_rate": successes / len(level_rows),
                "any_challenge_wilson_95": wilson_interval(successes, len(level_rows)),
                "explicit_challenge_count": explicit,
                "explicit_challenge_rate": explicit / len(level_rows),
                "mean_challenge_level": mean(
                    int(row["challenge_level"]) for row in level_rows
                ),
            }
        )
    return points


def empirical_crossing(curve: list[dict[str, Any]], rate: float = 0.5) -> int | None:
    for point in curve:
        if float(point["any_challenge_rate"]) >= rate:
            return int(point["surprisal_log10"])
    return None


def scenario_thresholds(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for scenario_id, scenario_rows in sorted(grouped(rows, "scenario_id").items()):
        level_groups = sorted(
            (
                int(level),
                sorted(values, key=lambda row: int(row.get("replicate", 1))),
            )
            for level, values in grouped(scenario_rows, "level").items()
        )
        rates = [
            mean(int(row["any_challenge"]) for row in level_rows)
            for _, level_rows in level_groups
        ]
        level_records = [level_rows[0] for _, level_rows in level_groups]
        first_index = next((i for i, rate in enumerate(rates) if rate > 0), None)
        sustained_index = next(
            (
                index
                for index in range(len(rates))
                if rates[index] > 0 and all(rate > 0 for rate in rates[index:])
            ),
            None,
        )
        s50_index = next((i for i, rate in enumerate(rates) if rate >= 0.5), None)
        sustained_s50_index = next(
            (
                index
                for index in range(len(rates))
                if rates[index] >= 0.5
                and all(rate >= 0.5 for rate in rates[index:])
            ),
            None,
        )
        drops = [max(0.0, left - right) for left, right in zip(rates, rates[1:])]
        replicate_counts = [len(level_rows) for _, level_rows in level_groups]
        if all(count == 1 for count in replicate_counts):
            pattern = "".join(str(int(rate)) for rate in rates)
        else:
            pattern = ",".join(f"{rate:.2f}" for rate in rates)
        output.append(
            {
                "scenario_id": scenario_id,
                "scenario_name": level_records[0]["scenario_name"],
                "replicates_per_level": replicate_counts,
                "challenge_rates": rates,
                "first_challenge_level": (
                    int(level_records[first_index]["level"])
                    if first_index is not None
                    else None
                ),
                "first_challenge_surprisal_log10": (
                    int(level_records[first_index]["surprisal_log10"])
                    if first_index is not None
                    else None
                ),
                "sustained_challenge_level": (
                    int(level_records[sustained_index]["level"])
                    if sustained_index is not None
                    else None
                ),
                "sustained_challenge_surprisal_log10": (
                    int(level_records[sustained_index]["surprisal_log10"])
                    if sustained_index is not None
                    else None
                ),
                "scenario_s50_level": (
                    int(level_records[s50_index]["level"])
                    if s50_index is not None
                    else None
                ),
                "scenario_s50_surprisal_log10": (
                    int(level_records[s50_index]["surprisal_log10"])
                    if s50_index is not None
                    else None
                ),
                "sustained_s50_surprisal_log10": (
                    int(level_records[sustained_s50_index]["surprisal_log10"])
                    if sustained_s50_index is not None
                    else None
                ),
                "challenge_pattern": pattern,
                "monotonic": all(
                    left <= right + 1e-12 for left, right in zip(rates, rates[1:])
                ),
                "reversal_mass": sum(drops),
                "largest_adjacent_reversal": max(drops, default=0.0),
                "challenged_at_highest_level": rates[-1] > 0,
                "highest_level_challenge_rate": rates[-1],
            }
        )
    return output


def tag_rates(rows: list[dict[str, Any]]) -> dict[str, float]:
    return {field: mean(int(row[field]) for row in rows) for field in TAG_FIELDS}


def response_key(row: dict[str, Any]) -> tuple[str, str]:
    replicate = int(row.get("replicate") or 1)
    response_id = str(row.get("response_id") or f"{row['prompt_id']}::r{replicate}")
    return str(row["target_model"]), response_id


def grader_curves(
    consensus_rows: list[dict[str, Any]], grader_rows: list[dict[str, Any]]
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    metadata = {response_key(row): row for row in consensus_rows}
    enriched: list[dict[str, Any]] = []
    for row in grader_rows:
        key = response_key(row)
        item = metadata[key]
        enriched.append(
            {
                **row,
                "level": int(item["level"]),
                "surprisal_log10": int(item["surprisal_log10"]),
                "any_challenge": int(row["challenge_level"]) >= 1,
            }
        )

    output: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for model, model_rows in grouped(enriched, "target_model").items():
        output[model] = {}
        for grader, rows in grouped(model_rows, "grader_slug").items():
            points: list[dict[str, Any]] = []
            for level, level_rows in sorted(
                ((int(level), values) for level, values in grouped(rows, "level").items())
            ):
                points.append(
                    {
                        "level": level,
                        "surprisal_log10": int(level_rows[0]["surprisal_log10"]),
                        "n": len(level_rows),
                        "any_challenge_rate": mean(
                            bool(row["any_challenge"]) for row in level_rows
                        ),
                    }
                )
            output[model][grader] = points
    return output


def duplicate_response_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    cells = grouped(rows, "prompt_id")
    duplicate_count = 0
    all_identical_cells = 0
    for cell_rows in cells.values():
        responses = [str(row["assistant_response"]).strip() for row in cell_rows]
        unique_count = len(set(responses))
        duplicate_count += len(responses) - unique_count
        all_identical_cells += int(len(responses) > 1 and unique_count == 1)
    return {
        "responses": len(rows),
        "model_prompt_cells": len(cells),
        "exact_duplicate_response_count": duplicate_count,
        "exact_duplicate_response_rate": duplicate_count / len(rows),
        "all_replicates_identical_cell_count": all_identical_cells,
    }


def quantile(values: list[float], probability: float) -> float:
    if not values:
        raise ValueError("values must not be empty")
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def scenario_cluster_bootstrap(
    consensus_rows: list[dict[str, Any]],
    iterations: int = 10_000,
    seed: int = 20_260_714,
) -> dict[str, Any]:
    model_rows = grouped(consensus_rows, "target_model")
    claude_model = next((model for model in model_rows if "claude" in model.lower()), None)
    gpt_model = next((model for model in model_rows if "gpt" in model.lower()), None)
    if claude_model is None or gpt_model is None:
        return {"status": "unavailable", "reason": "Expected Claude and GPT model ids"}

    scenario_ids = sorted({str(row["scenario_id"]) for row in consensus_rows})
    by_model_scenario = {
        model: grouped(rows, "scenario_id") for model, rows in model_rows.items()
    }
    reversal_by_model_scenario = {
        model: {
            str(row["scenario_id"]): float(row["reversal_mass"])
            for row in scenario_thresholds(rows)
        }
        for model, rows in model_rows.items()
    }

    rng = random.Random(seed)
    challenge_differences: list[float] = []
    reversal_differences: list[float] = []
    s50_differences: list[float] = []
    for _ in range(iterations):
        sample = [rng.choice(scenario_ids) for _ in scenario_ids]
        sampled_rows: dict[str, list[dict[str, Any]]] = {}
        for model in (claude_model, gpt_model):
            sampled_rows[model] = [
                row
                for scenario_id in sample
                for row in by_model_scenario[model][scenario_id]
            ]

        claude_rate = mean(
            int(row["any_challenge"]) for row in sampled_rows[claude_model]
        )
        gpt_rate = mean(int(row["any_challenge"]) for row in sampled_rows[gpt_model])
        challenge_differences.append(claude_rate - gpt_rate)

        claude_reversal = mean(
            reversal_by_model_scenario[claude_model][scenario_id]
            for scenario_id in sample
        )
        gpt_reversal = mean(
            reversal_by_model_scenario[gpt_model][scenario_id]
            for scenario_id in sample
        )
        reversal_differences.append(gpt_reversal - claude_reversal)

        claude_s50 = empirical_crossing(challenge_curve(sampled_rows[claude_model]))
        gpt_s50 = empirical_crossing(challenge_curve(sampled_rows[gpt_model]))
        if claude_s50 is not None and gpt_s50 is not None:
            s50_differences.append(float(gpt_s50 - claude_s50))

    def interval(values: list[float]) -> list[float] | None:
        if not values:
            return None
        return [quantile(values, 0.025), quantile(values, 0.975)]

    return {
        "status": "complete",
        "iterations": iterations,
        "seed": seed,
        "resampling_unit": "scenario family, paired across target models",
        "claude_minus_gpt_any_challenge_rate": {
            "percentile_95_interval": interval(challenge_differences),
            "share_above_zero": mean(value > 0 for value in challenge_differences),
        },
        "gpt_minus_claude_mean_reversal_mass": {
            "percentile_95_interval": interval(reversal_differences),
            "share_above_zero": mean(value > 0 for value in reversal_differences),
        },
        "gpt_minus_claude_empirical_s50": {
            "valid_resamples": len(s50_differences),
            "percentile_95_interval": interval(s50_differences),
            "share_above_zero": mean(value > 0 for value in s50_differences),
        },
    }


def analyze(
    consensus_rows: list[dict[str, Any]],
    grader_rows: list[dict[str, Any]],
    *,
    expected_replicates_per_cell: int = 3,
    criteria_source: str = "REPLICATION_PLAN.md",
) -> dict[str, Any]:
    models: dict[str, Any] = {}
    for model, rows in sorted(grouped(consensus_rows, "target_model").items()):
        curve = challenge_curve(rows)
        scenario_results = scenario_thresholds(rows)
        models[model] = {
            "n": len(rows),
            "replicates": sorted({int(row.get("replicate", 1)) for row in rows}),
            "overall_any_challenge_rate": mean(
                int(row["any_challenge"]) for row in rows
            ),
            "overall_soft_challenge_rate": mean(
                int(row["challenge_level"]) == 1 for row in rows
            ),
            "overall_explicit_challenge_rate": mean(
                int(row["explicit_challenge"]) for row in rows
            ),
            "empirical_s50_log10": empirical_crossing(curve),
            "curve": curve,
            "scenario_thresholds": scenario_results,
            "tag_rates": tag_rates(rows),
            "agreement": dict(Counter(str(row["level_agreement"]) for row in rows)),
            "duplicate_responses": duplicate_response_stats(rows),
        }
        models[model]["monotonic_scenario_count"] = sum(
            row["monotonic"] for row in models[model]["scenario_thresholds"]
        )
        models[model]["nonmonotonic_scenario_count"] = sum(
            not row["monotonic"] for row in models[model]["scenario_thresholds"]
        )
        models[model]["mean_reversal_mass"] = mean(
            float(row["reversal_mass"])
            for row in models[model]["scenario_thresholds"]
        )
        models[model]["total_reversal_mass"] = sum(
            float(row["reversal_mass"])
            for row in models[model]["scenario_thresholds"]
        )
        models[model]["largest_adjacent_reversal"] = max(
            float(row["largest_adjacent_reversal"])
            for row in models[model]["scenario_thresholds"]
        )

    sensitivity = grader_curves(consensus_rows, grader_rows)
    max_curve_deviation = 0.0
    for model, model_graders in sensitivity.items():
        consensus_curve = {
            int(point["level"]): float(point["any_challenge_rate"])
            for point in models[model]["curve"]
        }
        for points in model_graders.values():
            for point in points:
                deviation = abs(
                    float(point["any_challenge_rate"])
                    - consensus_curve[int(point["level"])]
                )
                max_curve_deviation = max(max_curve_deviation, deviation)

    cell_sizes = Counter(
        (str(row["target_model"]), str(row["prompt_id"]))
        for row in consensus_rows
    )
    claude_model = next((model for model in models if "claude" in model.lower()), None)
    gpt_model = next((model for model in models if "gpt" in model.lower()), None)
    decisions: dict[str, Any] = {"status": "unavailable"}
    if set(cell_sizes.values()) != {expected_replicates_per_cell}:
        decisions = {
            "status": "exploratory_only",
            "reason": (
                "Confirmatory rules require exactly "
                f"{expected_replicates_per_cell} responses per model-prompt cell"
            ),
        }
    elif claude_model is not None and gpt_model is not None:
        claude = models[claude_model]
        gpt = models[gpt_model]
        sensitivity_supported = (
            claude["empirical_s50_log10"] is not None
            and gpt["empirical_s50_log10"] is not None
            and claude["empirical_s50_log10"] < gpt["empirical_s50_log10"]
        )
        coherence_supported = (
            gpt["mean_reversal_mass"] > claude["mean_reversal_mass"]
            and gpt["monotonic_scenario_count"]
            < claude["monotonic_scenario_count"]
        )
        explicitness_supported = all(
            values["overall_explicit_challenge_rate"]
            < values["overall_soft_challenge_rate"]
            for values in (claude, gpt)
        )
        decisions = {
            "status": "complete",
            "hypothesis_1_sensitivity_supported": sensitivity_supported,
            "hypothesis_2_coherence_supported": coherence_supported,
            "hypothesis_3_explicitness_supported_descriptively": explicitness_supported,
            "criteria_source": criteria_source,
        }

    return {
        "counts": {
            "target_responses": len(consensus_rows),
            "grader_labels": len(grader_rows),
            "target_models": len(models),
            "scenario_families": len({row["scenario_id"] for row in consensus_rows}),
            "levels_per_scenario": len({int(row["level"]) for row in consensus_rows}),
            "model_prompt_cells": len(cell_sizes),
            "replicates_per_cell": sorted(set(cell_sizes.values())),
        },
        "models": models,
        "confirmatory_decisions": decisions,
        "scenario_cluster_bootstrap": scenario_cluster_bootstrap(consensus_rows),
        "grader_sensitivity": {
            "curves": sensitivity,
            "maximum_absolute_curve_deviation": max_curve_deviation,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--expected-replicates-per-cell", type=int, default=3)
    parser.add_argument("--criteria-source", default="REPLICATION_PLAN.md")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    consensus_rows = load_consensus(args.input_dir / "consensus_labels.csv")
    grader_rows = load_jsonl(args.input_dir / "grader_labels.jsonl")
    if args.expected_replicates_per_cell < 1:
        raise ValueError("--expected-replicates-per-cell must be positive")
    summary = analyze(
        consensus_rows,
        grader_rows,
        expected_replicates_per_cell=args.expected_replicates_per_cell,
        criteria_source=args.criteria_source,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(args.output.resolve())


if __name__ == "__main__":
    main()
