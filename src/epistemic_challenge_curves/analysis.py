"""Reproduce the paper's main results from the released consensus labels.

This module deliberately uses only Python's standard library. It does not call
any language model, require an API key, or modify the original response data.
"""

from __future__ import annotations

import csv
import math
import random
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from statistics import mean
from typing import Any, Callable, Iterable


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

SURPRISAL_LEVELS = (1, 2, 4, 6, 8, 10)
TAG_FIELDS = (
    "rarity_acknowledged",
    "conditional_language",
    "alternative_explanation",
    "safety_or_task_bypass",
    "accusatory",
)
INTEGER_FIELDS = (
    "level",
    "repetitions",
    "surprisal_log10",
    "challenge_level",
    "any_challenge",
    "explicit_challenge",
    *TAG_FIELDS,
)


def read_consensus(path: Path) -> list[dict[str, Any]]:
    """Read one released consensus-label CSV and convert numeric columns."""

    with path.open(encoding="utf-8", newline="") as handle:
        rows: list[dict[str, Any]] = list(csv.DictReader(handle))
    for row in rows:
        for field in INTEGER_FIELDS:
            row[field] = int(row[field])
        row["replicate"] = int(row.get("replicate") or 1)
    return rows


def grouped(
    rows: Iterable[dict[str, Any]], field: str
) -> dict[str, list[dict[str, Any]]]:
    """Group records by a named field."""

    output: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        output[str(row[field])].append(row)
    return dict(output)


def rate(
    rows: list[dict[str, Any]], predicate: Callable[[dict[str, Any]], bool]
) -> float:
    """Return the share of records for which ``predicate`` is true."""

    if not rows:
        raise ValueError("Cannot calculate a rate from zero rows")
    return mean(predicate(row) for row in rows)


def wilson_interval(
    successes: int, total: int, z: float = 1.959963984540054
) -> list[float]:
    """Return a two-sided Wilson score interval for a binomial proportion."""

    if total < 1:
        raise ValueError("Cannot calculate a Wilson interval from zero trials")
    if successes < 0 or successes > total:
        raise ValueError("Successes must be between zero and the total")
    proportion = successes / total
    z_squared = z**2
    denominator = 1 + z_squared / total
    centre = (proportion + z_squared / (2 * total)) / denominator
    radius = (
        z
        * math.sqrt(
            proportion * (1 - proportion) / total
            + z_squared / (4 * total**2)
        )
        / denominator
    )
    return [max(0.0, centre - radius), min(1.0, centre + radius)]


def validate_release_rows(
    rows: list[dict[str, Any]], expected_models: set[str], source: str
) -> None:
    """Check the sample size, model identities, and five-response cell design."""

    models = {str(row["target_model"]) for row in rows}
    if models != expected_models:
        raise ValueError(
            f"{source} contains models {sorted(models)}, expected {sorted(expected_models)}"
        )
    expected_rows = len(expected_models) * 36 * 5
    if len(rows) != expected_rows:
        raise ValueError(f"{source} contains {len(rows)} rows, expected {expected_rows}")
    cells = Counter((str(row["target_model"]), str(row["prompt_id"])) for row in rows)
    if len(cells) != len(expected_models) * 36 or set(cells.values()) != {5}:
        raise ValueError(f"{source} does not contain five responses in every cell")


def challenge_curve(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Calculate the six-point any-challenge curve for one model."""

    points: list[dict[str, Any]] = []
    by_surprisal = grouped(rows, "surprisal_log10")
    for surprisal in SURPRISAL_LEVELS:
        level_rows = by_surprisal.get(str(surprisal), [])
        if not level_rows:
            raise ValueError(f"No responses found at surprisal {surprisal}")
        challenged = sum(int(row["any_challenge"]) for row in level_rows)
        points.append(
            {
                "surprisal_log10": surprisal,
                "responses": len(level_rows),
                "any_challenge_count": challenged,
                "any_challenge_rate": challenged / len(level_rows),
                "any_challenge_wilson_95": wilson_interval(
                    challenged, len(level_rows)
                ),
            }
        )
    return points


def empirical_s50(curve: list[dict[str, Any]]) -> int | None:
    """Return the first tested surprisal with at least 50% challenge."""

    for point in curve:
        if float(point["any_challenge_rate"]) >= 0.5:
            return int(point["surprisal_log10"])
    return None


def model_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate the values reported for one model in the paper."""

    curve = challenge_curve(rows)
    any_count = sum(int(row["any_challenge"]) for row in rows)
    soft_count = sum(int(row["challenge_level"]) == 1 for row in rows)
    explicit_count = sum(int(row["explicit_challenge"]) for row in rows)
    return {
        "responses": len(rows),
        "any_challenge_count": any_count,
        "any_challenge_rate": any_count / len(rows),
        "any_challenge_wilson_95": wilson_interval(any_count, len(rows)),
        "soft_challenge_count": soft_count,
        "soft_challenge_rate": soft_count / len(rows),
        "explicit_challenge_count": explicit_count,
        "explicit_challenge_rate": explicit_count / len(rows),
        "empirical_s50_log10": empirical_s50(curve),
        "challenge_curve": curve,
        "tag_rates": {
            field: rate(rows, lambda row, name=field: bool(row[name]))
            for field in TAG_FIELDS
        },
    }


def quantile(values: list[float], probability: float) -> float:
    """Return a linearly interpolated quantile, matching the frozen analysis."""

    if not values:
        raise ValueError("Cannot calculate a quantile from zero values")
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def percentile_interval(values: list[float]) -> list[float] | None:
    """Return the frozen 2.5th and 97.5th percentile bounds."""

    if not values:
        return None
    return [quantile(values, 0.025), quantile(values, 0.975)]


def holdout_comparison(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare Claude and GPT in the clean holdout."""

    by_model = grouped(rows, "target_model")
    claude_rows = by_model[CLAUDE]
    gpt_rows = by_model[GPT]
    scenario_ids = sorted({str(row["scenario_id"]) for row in rows})

    def challenge_rate(selected: list[dict[str, Any]]) -> float:
        return rate(selected, lambda row: bool(row["any_challenge"]))

    family_gaps: dict[str, float] = {}
    leave_one_out_gaps: dict[str, float] = {}
    for scenario in scenario_ids:
        claude_family = [row for row in claude_rows if row["scenario_id"] == scenario]
        gpt_family = [row for row in gpt_rows if row["scenario_id"] == scenario]
        family_gaps[scenario] = challenge_rate(claude_family) - challenge_rate(gpt_family)

        claude_remaining = [row for row in claude_rows if row["scenario_id"] != scenario]
        gpt_remaining = [row for row in gpt_rows if row["scenario_id"] != scenario]
        leave_one_out_gaps[scenario] = (
            challenge_rate(claude_remaining) - challenge_rate(gpt_remaining)
        )

    by_model_scenario = {
        model: grouped(model_rows, "scenario_id")
        for model, model_rows in by_model.items()
    }
    rng = random.Random(20_260_714)
    bootstrap_gaps: list[float] = []
    for _ in range(10_000):
        sample = [rng.choice(scenario_ids) for _ in scenario_ids]
        sampled_claude = [
            row for scenario in sample for row in by_model_scenario[CLAUDE][scenario]
        ]
        sampled_gpt = [
            row for scenario in sample for row in by_model_scenario[GPT][scenario]
        ]
        bootstrap_gaps.append(
            challenge_rate(sampled_claude) - challenge_rate(sampled_gpt)
        )

    measures = {
        "any_challenge": {
            CLAUDE: challenge_rate(claude_rows),
            GPT: challenge_rate(gpt_rows),
        },
        "rarity_acknowledged": {
            CLAUDE: rate(claude_rows, lambda row: bool(row["rarity_acknowledged"])),
            GPT: rate(gpt_rows, lambda row: bool(row["rarity_acknowledged"])),
        },
        "conditional_language": {
            CLAUDE: rate(claude_rows, lambda row: bool(row["conditional_language"])),
            GPT: rate(gpt_rows, lambda row: bool(row["conditional_language"])),
        },
        "alternative_explanation": {
            CLAUDE: rate(claude_rows, lambda row: bool(row["alternative_explanation"])),
            GPT: rate(gpt_rows, lambda row: bool(row["alternative_explanation"])),
        },
        "explicit_challenge": {
            CLAUDE: rate(claude_rows, lambda row: bool(row["explicit_challenge"])),
            GPT: rate(gpt_rows, lambda row: bool(row["explicit_challenge"])),
        },
    }
    for values in measures.values():
        values["claude_minus_gpt"] = values[CLAUDE] - values[GPT]

    return {
        "overall_claude_minus_gpt": challenge_rate(claude_rows)
        - challenge_rate(gpt_rows),
        "family_specific_gaps": family_gaps,
        "leave_one_family_out_gaps": leave_one_out_gaps,
        "paired_family_bootstrap": {
            "iterations": 10_000,
            "seed": 20_260_714,
            "percentile_95_interval": percentile_interval(bootstrap_gaps),
            "share_above_zero": mean(value > 0 for value in bootstrap_gaps),
        },
        "behavior_measures": measures,
    }


def panel_bootstrap(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Reproduce the frozen four-model paired scenario-family bootstrap."""

    by_model = grouped(rows, "target_model")
    scenario_ids = sorted({str(row["scenario_id"]) for row in rows})
    by_model_scenario = {
        model: grouped(model_rows, "scenario_id")
        for model, model_rows in by_model.items()
    }
    rng = random.Random(20_260_715)
    samples = [
        [rng.choice(scenario_ids) for _ in scenario_ids] for _ in range(10_000)
    ]
    comparisons: dict[str, Any] = {}
    for left, right in combinations(MODEL_ORDER, 2):
        rate_differences: list[float] = []
        s50_differences: list[float] = []
        for sample in samples:
            left_rows = [
                row for scenario in sample for row in by_model_scenario[left][scenario]
            ]
            right_rows = [
                row for scenario in sample for row in by_model_scenario[right][scenario]
            ]
            rate_differences.append(
                rate(left_rows, lambda row: bool(row["any_challenge"]))
                - rate(right_rows, lambda row: bool(row["any_challenge"]))
            )
            left_s50 = empirical_s50(challenge_curve(left_rows))
            right_s50 = empirical_s50(challenge_curve(right_rows))
            if left_s50 is not None and right_s50 is not None:
                s50_differences.append(float(left_s50 - right_s50))

        key = f"{left}__minus__{right}"
        comparisons[key] = {
            "left_model": left,
            "right_model": right,
            "left_label": MODEL_LABELS[left],
            "right_label": MODEL_LABELS[right],
            "overall_challenge_rate_left_minus_right": {
                "percentile_95_interval": percentile_interval(rate_differences),
                "share_above_zero": mean(value > 0 for value in rate_differences),
            },
            "empirical_s50_left_minus_right": {
                "valid_resamples": len(s50_differences),
                "percentile_95_interval": percentile_interval(s50_differences),
                "share_above_zero": (
                    mean(value > 0 for value in s50_differences)
                    if s50_differences
                    else None
                ),
            },
        }
    return {
        "iterations": 10_000,
        "seed": 20_260_715,
        "resampling_unit": "scenario family, paired across all four target models",
        "comparisons": comparisons,
    }


def build_results(holdout_path: Path, extension_path: Path) -> dict[str, Any]:
    """Build all clean public results from the two released response datasets."""

    holdout_rows = read_consensus(holdout_path)
    extension_rows = read_consensus(extension_path)
    validate_release_rows(holdout_rows, {CLAUDE, GPT}, "clean holdout")
    validate_release_rows(extension_rows, {GROK, GLM}, "model extension")

    panel_rows = holdout_rows + extension_rows
    by_model = grouped(panel_rows, "target_model")

    def public_source_path(path: Path) -> str:
        """Keep public metadata useful without exposing a local computer path."""

        parts = path.parts
        for public_root in ("data", "outputs"):
            if public_root in parts:
                return Path(*parts[parts.index(public_root) :]).as_posix()
        return path.name

    return {
        "source_data": {
            "holdout_consensus_labels": public_source_path(holdout_path),
            "extension_consensus_labels": public_source_path(extension_path),
        },
        "counts": {
            "responses": len(panel_rows),
            "models": len(MODEL_ORDER),
            "scenario_families": len(
                {str(row["scenario_id"]) for row in panel_rows}
            ),
            "surprisal_levels": list(SURPRISAL_LEVELS),
        },
        "model_order": list(MODEL_ORDER),
        "model_labels": MODEL_LABELS,
        "models": {model: model_summary(by_model[model]) for model in MODEL_ORDER},
        "clean_holdout_comparison": holdout_comparison(holdout_rows),
        "pairwise_scenario_cluster_bootstrap": panel_bootstrap(panel_rows),
    }
