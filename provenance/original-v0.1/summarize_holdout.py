"""Create a compact, report-ready summary of the clean Module A holdout."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
HOLDOUT = ROOT / "outputs" / "module_a_holdout_v0_1"
OUTPUT = HOLDOUT / "confirmatory_summary.json"
CLAUDE = "openrouter/anthropic/claude-sonnet-5"
GPT = "openrouter/openai/gpt-5.6-terra"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def empirical_crossing(points: list[dict[str, Any]]) -> int | None:
    for point in points:
        if float(point["any_challenge_rate"]) >= 0.5:
            return int(point["surprisal_log10"])
    return None


def model_metrics(values: dict[str, Any]) -> dict[str, Any]:
    duplicate = values.get("duplicate_responses", {})
    return {
        "n": values["n"],
        "overall_any_challenge_rate": values["overall_any_challenge_rate"],
        "overall_soft_challenge_rate": values["overall_soft_challenge_rate"],
        "overall_explicit_challenge_rate": values[
            "overall_explicit_challenge_rate"
        ],
        "empirical_s50_log10": values["empirical_s50_log10"],
        "monotonic_scenario_count": values["monotonic_scenario_count"],
        "nonmonotonic_scenario_count": values["nonmonotonic_scenario_count"],
        "mean_reversal_mass": values["mean_reversal_mass"],
        "total_reversal_mass": values["total_reversal_mass"],
        "largest_adjacent_reversal": values["largest_adjacent_reversal"],
        "exact_duplicate_response_rate": duplicate.get(
            "exact_duplicate_response_rate"
        ),
        "agreement": values["agreement"],
        "tag_rates": values["tag_rates"],
    }


def main() -> None:
    analysis = load(HOLDOUT / "analysis_summary.json")
    scoring = load(HOLDOUT / "scoring" / "summary.json")
    validation = load(HOLDOUT / "target_validation.json")
    adjudication = load(HOLDOUT / "split_adjudication.json")
    prior = load(ROOT / "outputs" / "module_a_replication_v0_1" / "confirmatory_summary.json")

    grader_s50: dict[str, dict[str, int | None]] = {}
    for model, graders in analysis["grader_sensitivity"]["curves"].items():
        grader_s50[model] = {
            grader: empirical_crossing(points) for grader, points in graders.items()
        }

    holdout_models = {
        model: model_metrics(analysis["models"][model]) for model in (CLAUDE, GPT)
    }
    prior_models = {
        model: prior["models"][model]["combined_three_replicates"]
        for model in (CLAUDE, GPT)
    }
    bootstrap = analysis["scenario_cluster_bootstrap"]
    reversal_interval = bootstrap["gpt_minus_claude_mean_reversal_mass"][
        "percentile_95_interval"
    ]

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "plan": "HOLDOUT_PLAN.md",
        "freeze": "HOLDOUT_FREEZE.json",
        "primary_analysis": "clean holdout only",
        "counts": analysis["counts"],
        "target_validation": {
            "accepted": validation["accepted"],
            "total_samples": validation["total_samples"],
            "logs": validation["logs"],
        },
        "confirmatory_decisions": analysis["confirmatory_decisions"],
        "interpretation": {
            "sensitivity": "robustly_supported",
            "coherence": (
                "formal_rule_supported_but_not_robust"
                if analysis["confirmatory_decisions"][
                    "hypothesis_2_coherence_supported"
                ]
                and reversal_interval is not None
                and float(reversal_interval[0]) == 0
                else "see_primary_results"
            ),
            "explicitness": "supported_descriptively",
            "coherence_reason": (
                "Only one GPT scenario reversed, by 0.2; the paired "
                "scenario-bootstrap interval for excess reversal mass includes zero."
            ),
        },
        "models": {
            model: {
                "clean_holdout": holdout_models[model],
                "prior_combined_replication_context_only": prior_models[model],
            }
            for model in (CLAUDE, GPT)
        },
        "scenario_cluster_bootstrap": bootstrap,
        "grader_sensitivity": {
            "empirical_s50_log10": grader_s50,
            "maximum_absolute_curve_deviation": analysis["grader_sensitivity"][
                "maximum_absolute_curve_deviation"
            ],
        },
        "automated_scoring": {
            "counts": scoring["counts"],
            "pairwise_level_agreement": scoring["pairwise_level_agreement"],
            "three_way_split_count": adjudication["three_way_split_count"],
        },
        "costs_usd": {
            "usage_before_holdout": 29.407621235,
            "usage_after_target_generation": 30.461676235,
            "usage_after_scoring": 32.944441853,
            "target_generation": 1.054055,
            "automated_scoring_and_adjudication": 2.482765618,
            "total_holdout": 3.536820618,
            "remaining_allowance": 11.055558147,
        },
    }
    OUTPUT.write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(OUTPUT.resolve())


if __name__ == "__main__":
    main()
