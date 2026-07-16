"""Create one compact, source-backed summary of the confirmatory replication."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
PILOT = ROOT / "outputs" / "automated_scoring_v0_1" / "analysis_summary.json"
REPLICATION = ROOT / "outputs" / "module_a_replication_v0_1"
OUTPUT = REPLICATION / "confirmatory_summary.json"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def model_summary(values: dict[str, Any]) -> dict[str, Any]:
    return {
        "n": values["n"],
        "overall_any_challenge_rate": values["overall_any_challenge_rate"],
        "overall_soft_challenge_rate": values.get("overall_soft_challenge_rate"),
        "overall_explicit_challenge_rate": values["overall_explicit_challenge_rate"],
        "empirical_s50_log10": values["empirical_s50_log10"],
        "monotonic_scenario_count": values["monotonic_scenario_count"],
        "nonmonotonic_scenario_count": values["nonmonotonic_scenario_count"],
        "mean_reversal_mass": values.get("mean_reversal_mass"),
        "total_reversal_mass": values.get("total_reversal_mass"),
        "largest_adjacent_reversal": values.get("largest_adjacent_reversal"),
        "exact_duplicate_response_rate": values.get("duplicate_responses", {}).get(
            "exact_duplicate_response_rate"
        ),
        "agreement": values["agreement"],
        "tag_rates": values["tag_rates"],
    }


def main() -> None:
    pilot = load(PILOT)
    replication = load(REPLICATION / "analysis_summary.json")
    new_only = load(REPLICATION / "new_replicates_only_sensitivity.json")
    scoring = load(REPLICATION / "scoring_summary.json")
    adjudication = load(REPLICATION / "split_adjudication.json")

    models = sorted(replication["models"])
    output = {
        "generated_at": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "plan": "REPLICATION_PLAN.md",
        "counts": replication["counts"],
        "confirmatory_decisions": replication["confirmatory_decisions"],
        "models": {
            model: {
                "pilot": model_summary(pilot["models"][model]),
                "combined_three_replicates": model_summary(
                    replication["models"][model]
                ),
                "new_replicates_only": model_summary(new_only["models"][model]),
            }
            for model in models
        },
        "scenario_cluster_bootstrap": replication["scenario_cluster_bootstrap"],
        "new_only_scenario_cluster_bootstrap": new_only[
            "scenario_cluster_bootstrap"
        ],
        "grader_sensitivity": replication["grader_sensitivity"],
        "grader_agreement": scoring,
        "split_adjudication": adjudication,
        "openrouter_costs": {
            "usage_before_replication": 28.055257677,
            "usage_after_target_generation": 28.341185677,
            "usage_after_scoring_and_adjudication": 29.407621235,
            "target_generation": 0.285928,
            "scoring_and_adjudication": 1.066435558,
            "total_replication": 1.352363558,
            "remaining_after_replication": 14.592378765,
        },
    }
    OUTPUT.write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(OUTPUT.resolve())


if __name__ == "__main__":
    main()
