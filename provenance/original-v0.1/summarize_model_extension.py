"""Write a compact, durable summary of the completed four-model panel."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "outputs" / "module_a_model_extension_v0_1"
OUTPUT = OUTPUT_DIR / "confirmatory_summary.json"

BASELINE_USAGE = 32.944441853
POST_TARGET_USAGE = 33.915354299
FINAL_USAGE = 36.679753322
BUDGET_CAP = 5.50
ACCOUNT_REMAINING = 7.320246678


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def build_summary() -> dict[str, Any]:
    panel = load(OUTPUT_DIR / "panel_analysis.json")
    scoring = load(OUTPUT_DIR / "scoring" / "summary.json")
    adjudication = load(OUTPUT_DIR / "split_adjudication.json")
    validation = load(OUTPUT_DIR / "validation_summary.json")

    model_summaries: dict[str, Any] = {}
    for model_id in panel["model_order"]:
        values = panel["models"][model_id]
        model_summaries[model_id] = {
            "label": panel["model_labels"][model_id],
            "responses": values["n"],
            "any_challenge_count": values["overall_any_challenge_count"],
            "any_challenge_rate": values["overall_any_challenge_rate"],
            "any_challenge_wilson_95": values["overall_any_challenge_wilson_95"],
            "soft_challenge_rate": values["overall_soft_challenge_rate"],
            "explicit_challenge_rate": values["overall_explicit_challenge_rate"],
            "empirical_s50_log10": values["empirical_s50_log10"],
            "s50_status": (
                f"First crossing at {values['empirical_s50_log10']}"
                if values["empirical_s50_log10"] is not None
                else "No crossing through 10"
            ),
            "challenge_curve": [
                {
                    "surprisal_log10": point["surprisal_log10"],
                    "responses": point["n"],
                    "any_challenge_count": point["any_challenge_count"],
                    "any_challenge_rate": point["any_challenge_rate"],
                    "any_challenge_wilson_95": point["any_challenge_wilson_95"],
                    "explicit_challenge_rate": point["explicit_challenge_rate"],
                }
                for point in values["curve"]
            ],
            "monotonic_scenario_count": values["monotonic_scenario_count"],
            "mean_reversal_mass": values["mean_reversal_mass"],
        }

    agreement = scoring["counts"]["level_agreement"]
    target_attempt_cost = POST_TARGET_USAGE - BASELINE_USAGE
    total_cost = FINAL_USAGE - BASELINE_USAGE
    return {
        "generated_at": now_utc(),
        "study": "Module A controlled-odds four-model panel",
        "analysis_role": panel["analysis_role"],
        "criteria_source": panel["criteria_source"],
        "freeze_manifests": [
            "MODEL_EXTENSION_FREEZE.json",
            "MODEL_EXTENSION_FREEZE_V0_2.json",
            "MODEL_EXTENSION_FREEZE_V0_3.json",
            "ADJUDICATOR_FREEZE_V0_2.json",
        ],
        "validation_status": validation["status"],
        "validation": validation,
        "counts": panel["counts"],
        "models": model_summaries,
        "descriptive_s50_order": [
            panel["model_labels"][model_id]
            for model_id in panel["descriptive_ranking_earliest_s50"]
        ],
        "robust_interpretation": {
            "overall_challenge_rate_tiers": [
                ["Claude Sonnet 5"],
                ["GLM 5.2"],
                ["GPT-5.6 Terra", "Grok 4.5"],
            ],
            "aggregate_rate_conclusion": (
                "Claude exceeds GLM, GPT, and Grok; GLM exceeds GPT and Grok; "
                "GPT and Grok are not distinguishable on aggregate challenge rate "
                "under the paired scenario-family bootstrap."
            ),
            "curve_shape_conclusion": (
                "GPT and Grok have similar aggregate challenge rates but different "
                "curve shapes: GPT concentrates challenges at surprisal 10 and "
                "crosses 50%, while Grok rises gradually and never crosses 50%."
            ),
            "coherence_conclusion": (
                "Scenario-level reversal metrics are noisy at five responses per "
                "cell and remain secondary diagnostics, not robust model traits."
            ),
        },
        "paired_scenario_bootstrap": panel["pairwise_scenario_cluster_bootstrap"],
        "automated_grader_sensitivity": panel["grader_sensitivity"],
        "automated_scoring": {
            "graders": scoring["method"]["graders"],
            "consensus_rule": scoring["method"]["challenge_level"],
            "responses": scoring["counts"]["responses"],
            "grader_labels": scoring["counts"]["grader_labels"],
            "unanimous_count": agreement["unanimous"],
            "unanimous_rate": agreement["unanimous"] / scoring["counts"]["responses"],
            "majority_count": agreement["majority"],
            "three_way_split_count": agreement["three_way_split"],
            "pairwise_level_agreement": scoring["pairwise_level_agreement"],
            "adjudication": {
                "role": adjudication["role"],
                "split_count": adjudication["three_way_split_count"],
                "adjudicator": adjudication["adjudicator"],
                "matched_primary_median": adjudication["results"][0][
                    "matches_primary_median"
                ],
                "primary_label_changed": adjudication["results"][0][
                    "primary_label_changed"
                ],
            },
        },
        "cost_usd": {
            "target_attempts_including_rejected_runs": round(target_attempt_cost, 12),
            "scoring_retries_and_adjudication": round(
                FINAL_USAGE - POST_TARGET_USAGE, 12
            ),
            "total_extension": round(total_cost, 12),
            "frozen_incremental_cap": BUDGET_CAP,
            "under_cap_by": round(BUDGET_CAP - total_cost, 12),
            "openrouter_account_remaining_after_completion": ACCOUNT_REMAINING,
        },
        "limitations": panel["limitations"]
        + [
            "The GLM rerun used a 4,096-token ceiling after mechanically rejected lower-ceiling attempts; accepted Grok and the original holdout targets used 800 tokens.",
            "Empirical S50 is a discrete first crossing on six tested levels, not a fitted latent threshold.",
            "Five responses per model-prompt cell make scenario-level rates move in 0.2 increments.",
        ],
    }


def main() -> None:
    summary = build_summary()
    OUTPUT.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(OUTPUT.resolve())


if __name__ == "__main__":
    main()
