"""Build the MCP technical report for the clean Module A holdout."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from analyze_results import empirical_crossing


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "outputs" / "module_a_holdout_v0_1"
OUTPUT = RESULTS / "report_artifact.json"
CLAUDE = "openrouter/anthropic/claude-sonnet-5"
GPT = "openrouter/openai/gpt-5.6-terra"
MODEL_LABELS = {CLAUDE: "Claude Sonnet 5", GPT: "GPT-5.6 Terra"}
GRADER_LABELS = {
    "gemini_3_1_pro": "Gemini 3.1 Pro",
    "mistral_large_2512": "Mistral Large",
    "deepseek_v4_pro": "DeepSeek V4 Pro",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sources() -> list[dict[str, Any]]:
    return [
        {
            "id": "holdout_summary",
            "label": "Clean holdout confirmatory summary",
            "path": "outputs/module_a_holdout_v0_1/confirmatory_summary.json",
            "query": {
                "engine": "duckdb",
                "language": "sql",
                "sql": (
                    "SELECT * FROM read_json_auto("
                    "'outputs/module_a_holdout_v0_1/confirmatory_summary.json');"
                ),
                "description": (
                    "Loads the compact holdout results, prior-study context, "
                    "grader sensitivity, acceptance checks, and costs. Regenerate "
                    "with summarize_holdout.py."
                ),
                "tables_used": [
                    "outputs/module_a_holdout_v0_1/analysis_summary.json",
                    "outputs/module_a_holdout_v0_1/scoring/summary.json",
                    "outputs/module_a_replication_v0_1/confirmatory_summary.json",
                ],
                "filters": [
                    "Primary inference uses clean holdout responses only",
                    "Two target models, six unseen scenarios, six surprisal levels",
                    "Five responses per model-prompt cell",
                ],
                "metric_definitions": [
                    "Any challenge = consensus challenge_level >= 1.",
                    "Empirical S50 = first tested surprisal where aggregate challenge rate is at least 50%.",
                    "Reversal mass = sum of positive adjacent decreases in replicated challenge rate within a scenario.",
                    "Monotonic scenario = no adjacent decrease across the six tested levels.",
                ],
            },
        },
        {
            "id": "holdout_analysis",
            "label": "Clean holdout analysis",
            "path": "outputs/module_a_holdout_v0_1/analysis_summary.json",
            "query": {
                "engine": "duckdb",
                "language": "sql",
                "sql": (
                    "SELECT * FROM read_json_auto("
                    "'outputs/module_a_holdout_v0_1/analysis_summary.json');"
                ),
                "description": (
                    "Loads holdout challenge curves, Wilson intervals, scenario "
                    "reversal mass, cluster bootstrap, and grader sensitivity."
                ),
                "tables_used": [
                    "outputs/module_a_holdout_v0_1/scoring/consensus_labels.csv",
                    "outputs/module_a_holdout_v0_1/scoring/grader_labels.jsonl",
                ],
            },
        },
        {
            "id": "holdout_scoring",
            "label": "Holdout automated-grader agreement",
            "path": "outputs/module_a_holdout_v0_1/scoring/summary.json",
            "query": {
                "engine": "duckdb",
                "language": "sql",
                "sql": (
                    "SELECT * FROM read_json_auto("
                    "'outputs/module_a_holdout_v0_1/scoring/summary.json');"
                ),
                "description": (
                    "Loads consensus counts and pairwise ordinal agreement for all "
                    "360 holdout responses."
                ),
                "tables_used": [
                    "outputs/module_a_holdout_v0_1/scoring/consensus_labels.csv",
                    "outputs/module_a_holdout_v0_1/scoring/grader_labels.jsonl",
                ],
            },
        },
        {
            "id": "holdout_plan",
            "label": "Frozen clean holdout plan",
            "path": "HOLDOUT_PLAN.md",
        },
        {
            "id": "prior_replication",
            "label": "Prior three-response replication context",
            "path": "outputs/module_a_replication_v0_1/confirmatory_summary.json",
            "query": {
                "engine": "duckdb",
                "language": "sql",
                "sql": (
                    "SELECT * FROM read_json_auto("
                    "'outputs/module_a_replication_v0_1/confirmatory_summary.json');"
                ),
                "description": (
                    "Loads the earlier combined replication estimates for contextual "
                    "comparison only; these responses are not pooled with the holdout."
                ),
                "tables_used": [
                    "outputs/module_a_replication_v0_1/confirmatory_summary.json"
                ],
            },
        },
    ]


def build_artifact() -> dict[str, Any]:
    analysis = load(RESULTS / "analysis_summary.json")
    compact = load(RESULTS / "confirmatory_summary.json")
    scoring = load(RESULTS / "scoring" / "summary.json")
    prior = load(
        ROOT / "outputs" / "module_a_replication_v0_1" / "confirmatory_summary.json"
    )
    generated_at = now_utc()
    claude = analysis["models"][CLAUDE]
    gpt = analysis["models"][GPT]
    agreement = scoring["counts"]["level_agreement"]

    challenge_curve: list[dict[str, Any]] = []
    scenario_detail: list[dict[str, Any]] = []
    for model_id, values in analysis["models"].items():
        for point in values["curve"]:
            challenge_curve.append(
                {
                    "target_model": model_id,
                    "model": MODEL_LABELS[model_id],
                    "line_style": "solid" if model_id == CLAUDE else "dashed",
                    "level": point["level"],
                    "surprisal_log10": point["surprisal_log10"],
                    "odds_label": f"1 in 10^{point['surprisal_log10']}",
                    "responses": point["n"],
                    "scenario_families": 6,
                    "replicates_per_scenario": 5,
                    "challenge_count": point["any_challenge_count"],
                    "challenge_rate": point["any_challenge_rate"],
                    "wilson_95_low": point["any_challenge_wilson_95"][0],
                    "wilson_95_high": point["any_challenge_wilson_95"][1],
                    "explicit_challenge_rate": point["explicit_challenge_rate"],
                    "mean_challenge_level": point["mean_challenge_level"],
                }
            )
        for scenario in values["scenario_thresholds"]:
            scenario_detail.append(
                {
                    "target_model": model_id,
                    "model": MODEL_LABELS[model_id],
                    "scenario_id": scenario["scenario_id"],
                    "scenario": scenario["scenario_name"],
                    "challenge_rate_pattern": scenario["challenge_pattern"],
                    "reversal_mass": scenario["reversal_mass"],
                    "largest_adjacent_reversal": scenario[
                        "largest_adjacent_reversal"
                    ],
                    "monotonic": "Yes" if scenario["monotonic"] else "No",
                    "scenario_s50_log10": scenario[
                        "scenario_s50_surprisal_log10"
                    ],
                    "sustained_s50_log10": scenario[
                        "sustained_s50_surprisal_log10"
                    ],
                    "highest_level_challenge_rate": scenario[
                        "highest_level_challenge_rate"
                    ],
                    "responses": 30,
                }
            )

    study_comparison: list[dict[str, Any]] = []
    for model_id in (CLAUDE, GPT):
        prior_values = prior["models"][model_id]["combined_three_replicates"]
        holdout_values = analysis["models"][model_id]
        for study, values, responses_per_cell, primary_status in (
            (
                "Prior combined replication",
                prior_values,
                3,
                "Context only; includes pilot",
            ),
            ("Clean unseen-scenario holdout", holdout_values, 5, "Primary holdout"),
        ):
            study_comparison.append(
                {
                    "target_model": model_id,
                    "model": MODEL_LABELS[model_id],
                    "study": study,
                    "analysis_role": primary_status,
                    "responses": values["n"],
                    "responses_per_cell": responses_per_cell,
                    "challenge_rate": values["overall_any_challenge_rate"],
                    "explicit_challenge_rate": values[
                        "overall_explicit_challenge_rate"
                    ],
                    "empirical_s50_log10": values["empirical_s50_log10"],
                    "monotonic_scenarios": values["monotonic_scenario_count"],
                    "mean_reversal_mass": values["mean_reversal_mass"],
                }
            )

    grader_s50: list[dict[str, Any]] = []
    for model_id, graders in analysis["grader_sensitivity"]["curves"].items():
        for grader_slug, curve in graders.items():
            crossing = empirical_crossing(curve)
            grader_s50.append(
                {
                    "target_model": model_id,
                    "model": MODEL_LABELS[model_id],
                    "grader": GRADER_LABELS[grader_slug],
                    "grader_slug": grader_slug,
                    "empirical_s50_log10": crossing,
                    "crossing_status": (
                        f"Crossed at {crossing}"
                        if crossing is not None
                        else "No crossing through 10"
                    ),
                    "highest_level_challenge_rate": curve[-1][
                        "any_challenge_rate"
                    ],
                    "graded_responses": sum(point["n"] for point in curve),
                }
            )

    pairwise_agreement: list[dict[str, Any]] = []
    for pair, values in scoring["pairwise_level_agreement"].items():
        left, right = pair.split("__", maxsplit=1)
        pairwise_agreement.append(
            {
                "grader_pair": f"{GRADER_LABELS[left]} – {GRADER_LABELS[right]}",
                "responses": values["n"],
                "exact_agreement": values["exact_agreement"],
                "mean_absolute_level_difference": values[
                    "mean_absolute_difference"
                ],
            }
        )

    headline_metrics = [
        {
            "s50_gap": gpt["empirical_s50_log10"] - claude["empirical_s50_log10"],
            "claude_s50": claude["empirical_s50_log10"],
            "gpt_s50": gpt["empirical_s50_log10"],
            "challenge_rate_gap": (
                claude["overall_any_challenge_rate"]
                - gpt["overall_any_challenge_rate"]
            ),
            "claude_challenge_rate": claude["overall_any_challenge_rate"],
            "gpt_challenge_rate": gpt["overall_any_challenge_rate"],
            "gpt_reversal_mass": gpt["mean_reversal_mass"],
            "claude_reversal_mass": claude["mean_reversal_mass"],
            "gpt_monotonic": gpt["monotonic_scenario_count"],
            "claude_monotonic": claude["monotonic_scenario_count"],
            "unanimous_rate": agreement["unanimous"] / 360,
            "majority_rate": agreement["majority"] / 360,
        }
    ]

    source_list = sources()
    title = "Epistemic Challenge Curves — Clean Module A Holdout"
    manifest = {
        "version": 1,
        "surface": "report",
        "title": title,
        "description": (
            "Technical report testing whether epistemic sensitivity and threshold "
            "coherence generalize to six unseen controlled-odds scenarios."
        ),
        "generatedAt": generated_at,
        "cards": [
            {
                "id": "s50_gap_card",
                "description": (
                    "Difference between the two first tested surprisal levels at "
                    "which challenge reaches 50%."
                ),
                "dataset": "headline_metrics",
                "sourceId": "holdout_summary",
                "metrics": [
                    {"label": "Holdout S50 gap", "field": "s50_gap"},
                    {"label": "Claude", "field": "claude_s50"},
                    {"label": "GPT", "field": "gpt_s50"},
                ],
            },
            {
                "id": "challenge_gap_card",
                "description": (
                    "Difference in the share of 180 holdout responses classified "
                    "as any challenge."
                ),
                "dataset": "headline_metrics",
                "sourceId": "holdout_summary",
                "metrics": [
                    {
                        "label": "Challenge-rate gap",
                        "field": "challenge_rate_gap",
                        "format": "percent",
                    },
                    {
                        "label": "Claude",
                        "field": "claude_challenge_rate",
                        "format": "percent",
                    },
                    {
                        "label": "GPT",
                        "field": "gpt_challenge_rate",
                        "format": "percent",
                    },
                ],
            },
            {
                "id": "coherence_card",
                "description": (
                    "Mean GPT reversal mass; one of six GPT scenario curves "
                    "contained a 0.2 adjacent decrease."
                ),
                "dataset": "headline_metrics",
                "sourceId": "holdout_summary",
                "metrics": [
                    {"label": "GPT reversal mass", "field": "gpt_reversal_mass"},
                    {
                        "label": "Claude reversal mass",
                        "field": "claude_reversal_mass",
                    },
                    {"label": "GPT monotonic", "field": "gpt_monotonic"},
                    {"label": "Claude monotonic", "field": "claude_monotonic"},
                ],
            },
            {
                "id": "agreement_card",
                "description": (
                    "Share of 360 responses where all three automated graders "
                    "selected the same ordinal level."
                ),
                "dataset": "headline_metrics",
                "sourceId": "holdout_scoring",
                "metrics": [
                    {
                        "label": "Unanimous labels",
                        "field": "unanimous_rate",
                        "format": "percent",
                    },
                    {
                        "label": "Majority labels",
                        "field": "majority_rate",
                        "format": "percent",
                    },
                ],
            },
        ],
        "charts": [
            {
                "id": "challenge_curve_chart",
                "title": "Any-challenge rate across holdout surprisal levels",
                "subtitle": (
                    "Six unseen scenarios × five responses per model-level point; "
                    "Wilson intervals are available in tooltips."
                ),
                "showDescription": True,
                "type": "line",
                "intent": "comparison",
                "question": (
                    "Does the target-model sensitivity ordering generalize to "
                    "unseen controlled-odds scenarios?"
                ),
                "rationale": (
                    "A two-series line comparison shows the ordered response curve "
                    "over the six unevenly spaced surprisal levels."
                ),
                "comparisonContext": {
                    "grain": "Target model × surprisal level",
                    "denominator": "30 holdout responses per plotted point",
                    "unit": "Fraction classified as challenge level 1 or 2",
                },
                "dataset": "challenge_curve",
                "sourceId": "holdout_analysis",
                "encodings": {
                    "x": {
                        "field": "surprisal_log10",
                        "type": "quantitative",
                        "label": "Surprisal, −log10(p)",
                    },
                    "y": {
                        "field": "challenge_rate",
                        "type": "quantitative",
                        "label": "Any-challenge rate",
                        "format": "percent",
                    },
                    "color": {
                        "field": "model",
                        "type": "nominal",
                        "label": "Target model",
                    },
                    "lineStyle": {
                        "field": "line_style",
                        "type": "nominal",
                        "label": "Line style",
                    },
                    "tooltip": [
                        {"field": "odds_label", "type": "text", "label": "Nominal odds"},
                        {"field": "challenge_count", "type": "quantitative", "label": "Challenges"},
                        {"field": "responses", "type": "quantitative", "label": "Responses"},
                        {
                            "field": "explicit_challenge_rate",
                            "type": "quantitative",
                            "label": "Explicit challenge",
                            "format": "percent",
                        },
                        {
                            "field": "wilson_95_low",
                            "type": "quantitative",
                            "label": "Wilson 95% low",
                            "format": "percent",
                        },
                        {
                            "field": "wilson_95_high",
                            "type": "quantitative",
                            "label": "Wilson 95% high",
                            "format": "percent",
                        },
                    ],
                },
                "xAxisTitle": "Surprisal, −log10(p)",
                "yAxisTitle": "Any-challenge rate",
                "valueFormat": "percent",
                "layout": "full",
                "palette": {"kind": "categorical", "name": "blue-orange"},
                "legend": {"position": "bottom", "sort": "spec"},
                "settings": {"showPoints": "always"},
                "referenceLines": [
                    {
                        "axis": "y",
                        "value": 0.5,
                        "label": "50% empirical crossing",
                        "color": "neutral",
                        "lineStyle": "dotted",
                    }
                ],
                "surface": {"surface": "card", "viewMode": "both"},
            },
            {
                "id": "study_s50_chart",
                "title": "Empirical S50 in the prior replication and clean holdout",
                "subtitle": (
                    "Prior rows are contextual only; the holdout uses six unseen "
                    "scenario families and is analysed independently."
                ),
                "showDescription": True,
                "type": "bar",
                "intent": "comparison",
                "question": "Does the sensitivity ordering transfer across scenario sets?",
                "rationale": (
                    "Grouped bars compare the four discrete study–model crossings "
                    "without implying a fitted continuous threshold."
                ),
                "comparisonContext": {
                    "grain": "Study × target model",
                    "denominator": "108 prior or 180 holdout responses per model",
                    "unit": "Empirical S50, −log10(p)",
                },
                "dataset": "study_comparison",
                "sourceId": "holdout_summary",
                "encodings": {
                    "x": {"field": "study", "type": "nominal", "label": "Study"},
                    "y": {
                        "field": "empirical_s50_log10",
                        "type": "quantitative",
                        "label": "Empirical S50, −log10(p)",
                    },
                    "color": {
                        "field": "model",
                        "type": "nominal",
                        "label": "Target model",
                    },
                    "tooltip": [
                        {"field": "analysis_role", "type": "text", "label": "Analysis role"},
                        {"field": "responses", "type": "quantitative", "label": "Responses"},
                        {
                            "field": "challenge_rate",
                            "type": "quantitative",
                            "label": "Challenge rate",
                            "format": "percent",
                        },
                        {
                            "field": "mean_reversal_mass",
                            "type": "quantitative",
                            "label": "Mean reversal mass",
                        },
                    ],
                },
                "xAxisTitle": "Evidence set",
                "yAxisTitle": "Empirical S50, −log10(p)",
                "layout": "full",
                "palette": {"kind": "categorical", "name": "blue-orange"},
                "legend": {"position": "bottom", "sort": "spec"},
                "settings": {"groupMode": "grouped", "showValues": True},
                "surface": {"surface": "card", "viewMode": "both"},
            },
            {
                "id": "reversal_mass_chart",
                "title": "Scenario reversal mass in the clean holdout",
                "subtitle": (
                    "Five responses per level; only GPT's puzzle-button scenario "
                    "has a nonzero adjacent decrease."
                ),
                "showDescription": True,
                "type": "bar",
                "intent": "comparison",
                "question": "How broad is the holdout evidence for threshold incoherence?",
                "rationale": (
                    "Grouped scenario bars reveal that the formal coherence result "
                    "depends on one small exception rather than a broad pattern."
                ),
                "comparisonContext": {
                    "grain": "Target model × holdout scenario",
                    "denominator": "Five responses at each of six levels",
                    "unit": "Sum of positive adjacent challenge-rate decreases",
                },
                "dataset": "scenario_detail",
                "sourceId": "holdout_analysis",
                "encodings": {
                    "x": {"field": "scenario", "type": "nominal", "label": "Scenario family"},
                    "y": {
                        "field": "reversal_mass",
                        "type": "quantitative",
                        "label": "Reversal mass",
                    },
                    "color": {
                        "field": "model",
                        "type": "nominal",
                        "label": "Target model",
                    },
                    "tooltip": [
                        {"field": "challenge_rate_pattern", "type": "text", "label": "Level-wise rates"},
                        {"field": "largest_adjacent_reversal", "type": "quantitative", "label": "Largest adjacent reversal"},
                        {"field": "monotonic", "type": "text", "label": "Monotonic"},
                    ],
                },
                "xAxisTitle": "Holdout scenario family",
                "yAxisTitle": "Reversal mass",
                "layout": "full",
                "palette": {"kind": "categorical", "name": "blue-orange"},
                "legend": {"position": "bottom", "sort": "spec"},
                "settings": {"groupMode": "grouped", "showValues": True},
                "surface": {"surface": "card", "viewMode": "both"},
            },
        ],
        "tables": [
            {
                "id": "study_comparison_table",
                "title": "Prior and holdout estimates",
                "subtitle": (
                    "The two evidence sets are displayed together but are not pooled."
                ),
                "showDescription": True,
                "dataset": "study_comparison",
                "sourceId": "holdout_summary",
                "defaultSort": {"field": "model", "direction": "asc"},
                "density": "spacious",
                "layout": "full",
                "columns": [
                    {"field": "model", "label": "Target model", "type": "text"},
                    {"field": "study", "label": "Evidence set", "type": "text"},
                    {"field": "responses", "label": "Responses", "type": "number"},
                    {"field": "challenge_rate", "label": "Challenge rate", "format": "percent"},
                    {"field": "empirical_s50_log10", "label": "Empirical S50", "type": "number"},
                    {"field": "monotonic_scenarios", "label": "Monotonic scenarios", "type": "number"},
                    {"field": "mean_reversal_mass", "label": "Mean reversal mass", "type": "number"},
                ],
            },
            {
                "id": "scenario_detail_table",
                "title": "Holdout scenario-level coherence detail",
                "subtitle": (
                    "Challenge-rate patterns follow surprisal levels 1, 2, 4, 6, 8, and 10."
                ),
                "showDescription": True,
                "dataset": "scenario_detail",
                "sourceId": "holdout_analysis",
                "defaultSort": {"field": "reversal_mass", "direction": "desc"},
                "density": "compact",
                "layout": "full",
                "columns": [
                    {"field": "model", "label": "Target model", "type": "text"},
                    {"field": "scenario", "label": "Scenario", "type": "text"},
                    {"field": "challenge_rate_pattern", "label": "Challenge rates", "type": "text"},
                    {"field": "reversal_mass", "label": "Reversal mass", "type": "number"},
                    {"field": "monotonic", "label": "Monotonic", "type": "text"},
                    {"field": "scenario_s50_log10", "label": "Scenario S50", "type": "number"},
                ],
            },
            {
                "id": "grader_s50_table",
                "title": "Empirical S50 by automated grader",
                "subtitle": (
                    "Each grader labelled all 360 holdout responses; no crossing "
                    "means the challenge rate stayed below 50% through surprisal 10."
                ),
                "showDescription": True,
                "dataset": "grader_s50",
                "sourceId": "holdout_analysis",
                "defaultSort": {"field": "model", "direction": "asc"},
                "density": "spacious",
                "layout": "full",
                "columns": [
                    {"field": "model", "label": "Target model", "type": "text"},
                    {"field": "grader", "label": "Automated grader", "type": "text"},
                    {"field": "crossing_status", "label": "S50 result", "type": "text"},
                    {"field": "highest_level_challenge_rate", "label": "Challenge rate at 10", "format": "percent"},
                    {"field": "graded_responses", "label": "Responses graded", "type": "number"},
                ],
            },
            {
                "id": "grader_agreement_table",
                "title": "Pairwise automated-grader agreement",
                "subtitle": "Exact ordinal agreement across all 360 holdout responses.",
                "showDescription": True,
                "dataset": "pairwise_agreement",
                "sourceId": "holdout_scoring",
                "defaultSort": {"field": "exact_agreement", "direction": "desc"},
                "density": "spacious",
                "layout": "full",
                "columns": [
                    {"field": "grader_pair", "label": "Grader pair", "type": "text"},
                    {"field": "responses", "label": "Responses", "type": "number"},
                    {"field": "exact_agreement", "label": "Exact agreement", "format": "percent"},
                    {"field": "mean_absolute_level_difference", "label": "Mean absolute level difference", "type": "number"},
                ],
            },
        ],
        "sources": source_list,
        "blocks": [
            {"id": "title", "type": "markdown", "body": f"# {title}"},
            {
                "id": "technical_summary",
                "type": "markdown",
                "sourceId": "holdout_summary",
                "body": (
                    "## Technical summary\n\n"
                    "The clean holdout strongly supports a stable difference in **epistemic sensitivity**. Claude's empirical S50 is 2 and GPT's is 10; Claude challenged 77.2% of its 180 responses versus 11.1% for GPT. Across 10,000 paired scenario-cluster resamples, Claude's challenge-rate advantage is 56.1–76.1 percentage points and the GPT-minus-Claude S50 difference is 6–8 wherever both crossings are defined.\n\n"
                    "The preregistered **coherence** rule technically passes, but the independent evidence is weak. Claude has six monotonic curves and zero reversal mass; GPT has five monotonic curves and mean reversal mass 0.033. That GPT result comes from one 0.2 decrease in one scenario, and the bootstrap interval for excess reversal mass is 0–0.1. Sensitivity therefore generalizes cleanly; differential threshold incoherence should remain a diagnostic hypothesis rather than a confirmed headline claim."
                ),
            },
            {
                "id": "headline_metrics",
                "type": "metric-strip",
                "cardIds": [
                    "s50_gap_card",
                    "challenge_gap_card",
                    "coherence_card",
                    "agreement_card",
                ],
            },
            {
                "id": "sensitivity_finding",
                "type": "markdown",
                "sourceId": "holdout_analysis",
                "body": (
                    "## Epistemic sensitivity generalized to unseen scenarios\n\n"
                    "Claude reached the 50% challenge level at surprisal 2 and challenged every response from surprisal 4 onward. GPT remained below 7% through surprisal 8 and crossed 50% only at the highest tested level, 10. The separation is visible across the full curve, not merely at one threshold. Each plotted point contains 30 responses, and the tooltip Wilson intervals quantify response-level sampling uncertainty."
                ),
            },
            {"id": "challenge_curve", "type": "chart", "chartId": "challenge_curve_chart"},
            {
                "id": "transfer_finding",
                "type": "markdown",
                "sourceId": "holdout_summary",
                "body": (
                    "## The sensitivity ordering strengthened across scenario sets\n\n"
                    "The earlier combined replication placed Claude and GPT at S50 values 4 and 8. On the independently frozen holdout, the crossings moved outward to 2 and 10. The exact values are scenario-set dependent, but the ordering and substantive separation are stable. The prior estimates are shown only as context; no earlier response enters the holdout calculation."
                ),
            },
            {"id": "study_s50", "type": "chart", "chartId": "study_s50_chart"},
            {"id": "study_comparison", "type": "table", "tableId": "study_comparison_table"},
            {
                "id": "coherence_finding",
                "type": "markdown",
                "sourceId": "holdout_analysis",
                "body": (
                    "## The earlier coherence difference largely attenuated\n\n"
                    "The formal decision rule is satisfied because GPT has mean reversal mass 0.033 versus Claude's 0 and five versus six monotonic scenarios. But eleven of the twelve model–scenario curves are monotonic. The sole reversal is GPT's puzzle-button curve falling from 0.2 at surprisal 4 to 0 at 6—one challenged response out of five becoming none. Resampling only the six scenario families yields a 0–0.1 interval and a positive difference in 66.1% of draws. This is not robust confirmation of a general coherence difference."
                ),
            },
            {"id": "reversal_mass", "type": "chart", "chartId": "reversal_mass_chart"},
            {"id": "scenario_detail", "type": "table", "tableId": "scenario_detail_table"},
            {
                "id": "scope_definitions",
                "type": "markdown",
                "sourceId": "holdout_plan",
                "body": (
                    "## Scope, data, and metric definitions\n\n"
                    "- **Primary sample:** 360 new responses: two target models × 36 unseen prompts × five responses. No pilot or replication response is pooled.\n"
                    "- **Controlled surprisal:** −log₁₀(p) values 1, 2, 4, 6, 8, and 10 under prompt-stated uniform independent mechanisms.\n"
                    "- **Any challenge:** automated consensus level 1 or 2. Level 1 is a soft question or qualification; level 2 explicitly calls the account implausible or probably inaccurate.\n"
                    "- **Empirical S50:** the first tested surprisal with an aggregate challenge rate of at least 50%; it is not a fitted psychometric parameter.\n"
                    "- **Reversal mass:** the sum of positive adjacent decreases in a scenario's five-response challenge rate. Zero is monotonic over the tested levels."
                ),
            },
            {
                "id": "methodology",
                "type": "markdown",
                "sourceId": "holdout_plan",
                "body": (
                    "## Frozen experimental design and methodology\n\n"
                    "The hypotheses, prompts, models, sample size, settings, automated graders, consensus rule, metrics, bootstrap seed, and decision rules were written and SHA-256 hashed before any holdout target response was generated. Inspect ran five fresh one-shot epochs per prompt with no tools or retrieval, hidden reasoning disabled, and an 800-token ceiling. All 360 responses completed normally with no error, empty output, truncation, or attached score.\n\n"
                    "Three frozen graders labelled every response at temperature 0 and seed 42. The ordinal median determines challenge level; tag majorities determine diagnostics. Wilson intervals describe each 30-response curve point. The preregistered 10,000-draw paired scenario-cluster bootstrap resamples the six holdout families while preserving target-model pairing."
                ),
            },
            {
                "id": "grader_validation",
                "type": "markdown",
                "sourceId": "holdout_scoring",
                "body": (
                    "## Grader choice preserves the sensitivity ordering, not every magnitude\n\n"
                    "The graders were unanimous on 258 of 360 responses (71.7%) and reached a two-of-three majority on the remaining 102; no three-way split occurred. Pairwise exact agreement ranges from 79.2% to 84.2%. Grader-specific Claude S50 values are 2 or 4. GPT crosses at 8 under Gemini, 10 under Mistral, and does not cross through 10 under DeepSeek. Every grader therefore preserves the earlier-Claude ordering, although the maximum single-grader curve deviation from the ensemble is 46.7 percentage points, so exact curve magnitudes remain grader-sensitive."
                ),
            },
            {"id": "grader_s50", "type": "table", "tableId": "grader_s50_table"},
            {"id": "grader_agreement", "type": "table", "tableId": "grader_agreement_table"},
            {
                "id": "limitations",
                "type": "markdown",
                "body": (
                    "## Limitations, uncertainty, and robustness\n\n"
                    "- **Coherence evidence is sparse.** The formal GPT–Claude difference is driven by one response transition in one scenario, and its bootstrap interval includes zero.\n"
                    "- **S50 is discretized and edge-limited.** GPT first crosses at the highest tested level; the benchmark cannot locate a higher latent threshold.\n"
                    "- **Five responses remain coarse.** Scenario-level rates move in increments of 0.2.\n"
                    "- **Only six families are resampled.** Bootstrap intervals measure sensitivity to this frozen scenario set, not all possible testimony.\n"
                    "- **Automated agreement is internal reliability.** Human scoring is neither used nor required, but the ensemble does not by itself establish external construct validity.\n"
                    "- **Scope is deliberately narrow.** Results cover two routed models, first-person controlled-odds claims, and one-shot conversations."
                ),
            },
            {
                "id": "next_steps",
                "type": "markdown",
                "body": (
                    "## Recommended next steps\n\n"
                    "1. **Center the literature claim on epistemic sensitivity.** The clean holdout provides strong evidence that models can have substantially different intervention curves even when probability is controlled.\n"
                    "2. **Retain reversal mass as a diagnostic, not a confirmed model trait.** It detected a meaningful pilot pattern but did not generalize strongly enough to support the same headline claim.\n"
                    "3. **Run Module B as a separate external-validity study.** Test whether the sensitivity ordering survives when odds must come from background knowledge, while keeping empirical natural-event rates separate from exact lottery odds.\n"
                    "4. **Add more target models before publication.** A broader model panel would show whether the observed separation is a spectrum, a provider effect, or specific to this pair."
                ),
            },
            {
                "id": "further_questions",
                "type": "markdown",
                "body": (
                    "## Further questions\n\n"
                    "- Does the sensitivity ordering persist for third-person and reported-news claims?\n"
                    "- Do implicit real-world odds compress or widen the model gap?\n"
                    "- Is GPT's low challenge rate a stable conversational policy or partly an automated-rubric boundary effect?\n"
                    "- Would sequential escalation change sensitivity by making accumulated evidence more salient?"
                ),
            },
        ],
    }

    return {
        "surface": "report",
        "manifest": manifest,
        "snapshot": {
            "version": 1,
            "generatedAt": generated_at,
            "status": "ready",
            "datasets": {
                "headline_metrics": headline_metrics,
                "challenge_curve": challenge_curve,
                "study_comparison": study_comparison,
                "scenario_detail": scenario_detail,
                "grader_s50": grader_s50,
                "pairwise_agreement": pairwise_agreement,
            },
        },
        "sources": source_list,
    }


def main() -> None:
    artifact = build_artifact()
    OUTPUT.write_text(
        json.dumps(artifact, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(OUTPUT.resolve())


if __name__ == "__main__":
    main()
