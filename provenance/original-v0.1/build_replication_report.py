"""Build the MCP technical report for the Module A confirmatory replication."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from analyze_results import empirical_crossing


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "outputs" / "module_a_replication_v0_1"
OUTPUT = RESULTS / "report_artifact.json"
MODEL_LABELS = {
    "openrouter/anthropic/claude-sonnet-5": "Claude Sonnet 5",
    "openrouter/openai/gpt-5.6-terra": "GPT-5.6 Terra",
}
GRADER_LABELS = {
    "gemini_3_1_pro": "Gemini 3.1 Pro",
    "mistral_large_2512": "Mistral Large",
    "deepseek_v4_pro": "DeepSeek V4 Pro",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def source_specs() -> list[dict[str, Any]]:
    return [
        {
            "id": "confirmatory_summary",
            "label": "Confirmatory replication summary",
            "path": "outputs/module_a_replication_v0_1/confirmatory_summary.json",
            "query": {
                "engine": "duckdb",
                "language": "sql",
                "sql": (
                    "SELECT * FROM read_json_auto("
                    "'outputs/module_a_replication_v0_1/confirmatory_summary.json');"
                ),
                "description": (
                    "Loads the compact comparison of pilot, combined three-replicate, "
                    "and new-only sensitivity results. Regenerate with summarize_replication.py."
                ),
                "tables_used": [
                    "outputs/automated_scoring_v0_1/analysis_summary.json",
                    "outputs/module_a_replication_v0_1/analysis_summary.json",
                    "outputs/module_a_replication_v0_1/new_replicates_only_sensitivity.json",
                    "outputs/module_a_replication_v0_1/scoring_summary.json",
                    "outputs/module_a_replication_v0_1/split_adjudication.json",
                ],
                "filters": [
                    "Module A controlled-odds prompts only",
                    "Two target models, six scenarios, six surprisal levels",
                    "Three responses per model-prompt cell in the primary analysis",
                ],
                "metric_definitions": [
                    "Any challenge = consensus challenge_level >= 1.",
                    "Empirical S50 = first tested surprisal where aggregate any-challenge rate is at least 50%.",
                    "Scenario reversal mass = sum of all positive adjacent decreases in challenge rate as surprisal rises.",
                    "A scenario is monotonic when its challenge rate never decreases across adjacent levels.",
                ],
            },
        },
        {
            "id": "replication_analysis",
            "label": "Three-replicate analysis",
            "path": "outputs/module_a_replication_v0_1/analysis_summary.json",
            "query": {
                "engine": "duckdb",
                "language": "sql",
                "sql": (
                    "SELECT * FROM read_json_auto("
                    "'outputs/module_a_replication_v0_1/analysis_summary.json');"
                ),
                "description": (
                    "Loads challenge curves, scenario reversal mass, Wilson intervals, "
                    "cluster-bootstrap uncertainty, and grader-sensitivity results."
                ),
                "tables_used": [
                    "outputs/module_a_replication_v0_1/consensus_labels.csv",
                    "outputs/module_a_replication_v0_1/grader_labels.jsonl",
                ],
            },
        },
        {
            "id": "scoring_summary",
            "label": "Automated ensemble agreement",
            "path": "outputs/module_a_replication_v0_1/scoring_summary.json",
            "query": {
                "engine": "duckdb",
                "language": "sql",
                "sql": (
                    "SELECT * FROM read_json_auto("
                    "'outputs/module_a_replication_v0_1/scoring_summary.json');"
                ),
                "description": "Loads consensus counts and pairwise grader agreement for 216 responses.",
                "tables_used": [
                    "outputs/module_a_replication_v0_1/consensus_labels.csv",
                    "outputs/module_a_replication_v0_1/grader_labels.jsonl",
                ],
            },
        },
        {
            "id": "replication_plan",
            "label": "Frozen replication plan",
            "path": "REPLICATION_PLAN.md",
        },
    ]


def build_artifact() -> dict[str, Any]:
    analysis = json.loads((RESULTS / "analysis_summary.json").read_text(encoding="utf-8"))
    compact = json.loads((RESULTS / "confirmatory_summary.json").read_text(encoding="utf-8"))
    scoring = json.loads((RESULTS / "scoring_summary.json").read_text(encoding="utf-8"))
    generated_at = now_utc()

    claude_id = "openrouter/anthropic/claude-sonnet-5"
    gpt_id = "openrouter/openai/gpt-5.6-terra"
    claude = analysis["models"][claude_id]
    gpt = analysis["models"][gpt_id]
    bootstrap = analysis["scenario_cluster_bootstrap"]
    agreement = scoring["counts"]["level_agreement"]

    challenge_curve: list[dict[str, Any]] = []
    reversal_mass: list[dict[str, Any]] = []
    scenario_detail: list[dict[str, Any]] = []
    for model_id, values in analysis["models"].items():
        model_label = MODEL_LABELS[model_id]
        for point in values["curve"]:
            challenge_curve.append(
                {
                    "target_model": model_id,
                    "model": model_label,
                    "line_style": "solid" if model_id == claude_id else "dashed",
                    "level": point["level"],
                    "surprisal_log10": point["surprisal_log10"],
                    "odds_label": f"1 in 10^{point['surprisal_log10']}",
                    "responses": point["n"],
                    "scenario_families": 6,
                    "replicates_per_scenario": 3,
                    "challenge_count": point["any_challenge_count"],
                    "challenge_rate": point["any_challenge_rate"],
                    "wilson_95_low": point["any_challenge_wilson_95"][0],
                    "wilson_95_high": point["any_challenge_wilson_95"][1],
                    "explicit_challenge_rate": point["explicit_challenge_rate"],
                    "mean_challenge_level": point["mean_challenge_level"],
                }
            )
        for scenario in values["scenario_thresholds"]:
            row = {
                "target_model": model_id,
                "model": model_label,
                "scenario_id": scenario["scenario_id"],
                "scenario": scenario["scenario_name"],
                "challenge_rate_pattern": scenario["challenge_pattern"],
                "reversal_mass": scenario["reversal_mass"],
                "largest_adjacent_reversal": scenario[
                    "largest_adjacent_reversal"
                ],
                "monotonic": "Yes" if scenario["monotonic"] else "No",
                "scenario_s50_log10": scenario["scenario_s50_surprisal_log10"],
                "sustained_s50_log10": scenario[
                    "sustained_s50_surprisal_log10"
                ],
                "highest_level_challenge_rate": scenario[
                    "highest_level_challenge_rate"
                ],
                "responses": 18,
            }
            reversal_mass.append(row)
            scenario_detail.append(row)

    phase_comparison: list[dict[str, Any]] = []
    phase_labels = {
        "pilot": "Pilot (1 response/cell)",
        "new_replicates_only": "New responses only (2/cell)",
        "combined_three_replicates": "Pre-registered combined (3/cell)",
    }
    for model_id, phases in compact["models"].items():
        for phase_id in ("pilot", "new_replicates_only", "combined_three_replicates"):
            values = phases[phase_id]
            phase_comparison.append(
                {
                    "target_model": model_id,
                    "model": MODEL_LABELS[model_id],
                    "phase": phase_labels[phase_id],
                    "phase_id": phase_id,
                    "responses": values["n"],
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
            grader_s50.append(
                {
                    "target_model": model_id,
                    "model": MODEL_LABELS[model_id],
                    "grader": GRADER_LABELS[grader_slug],
                    "grader_slug": grader_slug,
                    "empirical_s50_log10": empirical_crossing(curve),
                    "graded_responses": sum(point["n"] for point in curve),
                }
            )

    pairwise_agreement = []
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
            "claude_challenge_rate": claude["overall_any_challenge_rate"],
            "gpt_challenge_rate": gpt["overall_any_challenge_rate"],
            "claude_s50": claude["empirical_s50_log10"],
            "gpt_s50": gpt["empirical_s50_log10"],
            "claude_reversal_mass": claude["mean_reversal_mass"],
            "gpt_reversal_mass": gpt["mean_reversal_mass"],
            "claude_monotonic": claude["monotonic_scenario_count"],
            "gpt_monotonic": gpt["monotonic_scenario_count"],
            "unanimous_rate": agreement["unanimous"] / 216,
            "majority_rate": agreement["majority"] / 216,
            "three_way_split_rate": agreement["three_way_split"] / 216,
        }
    ]

    sources = source_specs()
    title = "Epistemic Challenge Curves — Module A Replication"
    manifest = {
        "version": 1,
        "surface": "report",
        "title": title,
        "description": (
            "Technical report testing pre-registered sensitivity and coherence hypotheses "
            "with three automated responses per model-prompt cell."
        ),
        "generatedAt": generated_at,
        "cards": [
            {
                "id": "challenge_rate_card",
                "description": "Share of 108 responses per target model classified as any challenge.",
                "dataset": "headline_metrics",
                "sourceId": "confirmatory_summary",
                "metrics": [
                    {
                        "label": "Claude challenge rate",
                        "field": "claude_challenge_rate",
                        "format": "percent",
                    },
                    {
                        "label": "GPT challenge rate",
                        "field": "gpt_challenge_rate",
                        "format": "percent",
                    },
                ],
            },
            {
                "id": "s50_card",
                "description": "First tested −log10(p) with an aggregate challenge rate of at least 50%.",
                "dataset": "headline_metrics",
                "sourceId": "confirmatory_summary",
                "metrics": [
                    {"label": "Claude empirical S50", "field": "claude_s50"},
                    {"label": "GPT empirical S50", "field": "gpt_s50"},
                ],
            },
            {
                "id": "reversal_mass_card",
                "description": "Mean adjacent challenge-rate decrease summed within each scenario.",
                "dataset": "headline_metrics",
                "sourceId": "confirmatory_summary",
                "metrics": [
                    {"label": "GPT reversal mass", "field": "gpt_reversal_mass"},
                    {"label": "Claude reversal mass", "field": "claude_reversal_mass"},
                ],
            },
            {
                "id": "coherence_card",
                "description": "Scenario curves with no challenge-rate decrease across adjacent levels.",
                "dataset": "headline_metrics",
                "sourceId": "confirmatory_summary",
                "metrics": [
                    {"label": "Claude monotonic", "field": "claude_monotonic"},
                    {"label": "GPT monotonic", "field": "gpt_monotonic"},
                ],
            },
            {
                "id": "agreement_card",
                "description": "Responses where all three automated graders selected the same level.",
                "dataset": "headline_metrics",
                "sourceId": "scoring_summary",
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
                "title": "Any-challenge rate across controlled surprisal levels",
                "subtitle": "Six scenario families × three responses per model-level point; Wilson intervals are available in tooltips.",
                "showDescription": True,
                "type": "line",
                "intent": "comparison",
                "question": "Did the two target models retain distinct epistemic challenge sensitivity after replication?",
                "rationale": "The ordered, unevenly spaced surprisal ladder is best represented as a two-series line comparison.",
                "comparisonContext": {
                    "grain": "Target model × surprisal level",
                    "denominator": "18 responses per plotted point",
                    "unit": "Fraction classified as challenge level 1 or 2",
                },
                "dataset": "challenge_curve",
                "sourceId": "replication_analysis",
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
                    "color": {"field": "model", "type": "nominal", "label": "Target model"},
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
                "id": "reversal_mass_chart",
                "title": "Scenario reversal mass by target model",
                "subtitle": "Six scenario families; zero indicates a monotonic non-decreasing challenge curve.",
                "showDescription": True,
                "type": "bar",
                "intent": "comparison",
                "question": "Which scenario families contain challenge-to-accommodation reversals?",
                "rationale": "Grouped bars compare exact non-negative reversal magnitudes across six named scenarios and two models.",
                "comparisonContext": {
                    "grain": "Target model × scenario family",
                    "denominator": "Three responses at each of six levels",
                    "unit": "Sum of positive adjacent challenge-rate decreases",
                },
                "dataset": "reversal_mass",
                "sourceId": "replication_analysis",
                "encodings": {
                    "x": {"field": "scenario", "type": "nominal", "label": "Scenario family"},
                    "y": {
                        "field": "reversal_mass",
                        "type": "quantitative",
                        "label": "Reversal mass",
                    },
                    "color": {"field": "model", "type": "nominal", "label": "Target model"},
                    "tooltip": [
                        {"field": "challenge_rate_pattern", "type": "text", "label": "Level-wise rates"},
                        {
                            "field": "largest_adjacent_reversal",
                            "type": "quantitative",
                            "label": "Largest adjacent reversal",
                        },
                        {"field": "monotonic", "type": "text", "label": "Monotonic"},
                    ],
                },
                "xAxisTitle": "Scenario family",
                "yAxisTitle": "Reversal mass",
                "layout": "full",
                "palette": {"kind": "categorical", "name": "blue-orange"},
                "legend": {"position": "bottom", "sort": "spec"},
                "settings": {"groupMode": "grouped", "showValues": True},
                "surface": {"surface": "card", "viewMode": "both"},
            },
            {
                "id": "grader_s50_chart",
                "title": "Empirical S50 by automated grader",
                "subtitle": "Each grader labelled all 216 target responses; the ensemble median remains primary.",
                "showDescription": True,
                "type": "bar",
                "intent": "comparison",
                "question": "Is the target-model sensitivity ordering robust to grader choice?",
                "rationale": "Grouped bars expose the six discrete grader–target-model crossings without implying a continuous fitted parameter.",
                "comparisonContext": {
                    "grain": "Automated grader × target model",
                    "denominator": "216 target responses per grader",
                    "unit": "−log10(p)",
                },
                "dataset": "grader_s50",
                "sourceId": "replication_analysis",
                "encodings": {
                    "x": {"field": "grader", "type": "nominal", "label": "Automated grader"},
                    "y": {
                        "field": "empirical_s50_log10",
                        "type": "quantitative",
                        "label": "Empirical S50, −log10(p)",
                    },
                    "color": {"field": "model", "type": "nominal", "label": "Target model"},
                    "tooltip": [
                        {"field": "graded_responses", "type": "quantitative", "label": "Responses graded"}
                    ],
                },
                "xAxisTitle": "Automated grader",
                "yAxisTitle": "Empirical S50, −log10(p)",
                "layout": "full",
                "palette": {"kind": "categorical", "name": "blue-orange"},
                "legend": {"position": "bottom", "sort": "spec"},
                "settings": {"groupMode": "grouped", "showValues": True},
                "surface": {"surface": "card", "viewMode": "both"},
            },
        ],
        "tables": [
            {
                "id": "phase_comparison_table",
                "title": "Pilot, new-only, and combined estimates",
                "subtitle": "The new-only rows exclude every response used to discover the hypotheses.",
                "showDescription": True,
                "dataset": "phase_comparison",
                "sourceId": "confirmatory_summary",
                "defaultSort": {"field": "model", "direction": "asc"},
                "density": "compact",
                "layout": "full",
                "columns": [
                    {"field": "model", "label": "Target model", "type": "text"},
                    {"field": "phase", "label": "Evidence slice", "type": "text"},
                    {"field": "responses", "label": "Responses", "type": "number"},
                    {"field": "challenge_rate", "label": "Challenge rate", "format": "percent"},
                    {"field": "empirical_s50_log10", "label": "Empirical S50", "type": "number"},
                    {"field": "monotonic_scenarios", "label": "Monotonic scenarios", "type": "number"},
                    {"field": "mean_reversal_mass", "label": "Mean reversal mass", "type": "number"},
                ],
            },
            {
                "id": "scenario_detail_table",
                "title": "Scenario-level coherence detail",
                "subtitle": "Challenge-rate patterns follow surprisal levels 1, 2, 4, 6, 8, and 10.",
                "showDescription": True,
                "dataset": "scenario_detail",
                "sourceId": "replication_analysis",
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
                "id": "grader_agreement_table",
                "title": "Pairwise automated-grader agreement",
                "subtitle": "Exact ordinal agreement across all 216 target responses.",
                "showDescription": True,
                "dataset": "pairwise_agreement",
                "sourceId": "scoring_summary",
                "defaultSort": {"field": "exact_agreement", "direction": "desc"},
                "density": "compact",
                "layout": "full",
                "columns": [
                    {"field": "grader_pair", "label": "Grader pair", "type": "text"},
                    {"field": "responses", "label": "Responses", "type": "number"},
                    {"field": "exact_agreement", "label": "Exact agreement", "format": "percent"},
                    {
                        "field": "mean_absolute_level_difference",
                        "label": "Mean absolute level difference",
                        "type": "number",
                    },
                ],
            },
        ],
        "sources": sources,
        "blocks": [
            {"id": "title", "type": "markdown", "body": f"# {title}"},
            {
                "id": "technical_summary",
                "type": "markdown",
                "sourceId": "confirmatory_summary",
                "body": (
                    "## Technical summary\n\n"
                    "Both pre-registered decision rules were satisfied in the three-response-per-cell analysis. Claude's empirical S50 was 4 versus 8 for GPT, and Claude challenged 72.2% of responses versus 25.9% for GPT. Claude had zero reversal mass and six of six monotonic scenario curves; GPT had mean reversal mass 0.222 and only two of six monotonic curves. A paired scenario bootstrap placed Claude's challenge-rate advantage at 32.4–59.3 percentage points and GPT's excess mean reversal mass at 0.111–0.333.\n\n"
                    "The result supports measuring **epistemic sensitivity** and **threshold coherence** as separate properties. It is not a fully independent confirmation because the pre-registered primary analysis intentionally retained the exploratory pilot response as one of three replicates. The two newly generated responses per cell nevertheless preserve the same model ordering and the same direction of the coherence difference."
                ),
            },
            {
                "id": "headline_metrics",
                "type": "metric-strip",
                "cardIds": [
                    "challenge_rate_card",
                    "s50_card",
                    "reversal_mass_card",
                    "coherence_card",
                    "agreement_card",
                ],
            },
            {
                "id": "sensitivity_finding",
                "type": "markdown",
                "sourceId": "replication_analysis",
                "body": (
                    "## The sensitivity ordering survived replication\n\n"
                    "Claude crossed the 50% challenge level at surprisal 4, while GPT crossed at 8. The gap is not just a threshold artifact: Claude's overall challenge rate exceeded GPT's by 46.3 points. The bootstrap interval excludes zero, although it resamples only six scenario families and therefore describes robustness to scenario composition rather than a broad population of prompts. The chart shows 18 responses per point; tooltip intervals are Wilson intervals over those 18 responses."
                ),
            },
            {"id": "challenge_curve", "type": "chart", "chartId": "challenge_curve_chart"},
            {
                "id": "coherence_finding",
                "type": "markdown",
                "sourceId": "replication_analysis",
                "body": (
                    "## Threshold coherence replicated at the scenario level\n\n"
                    "Claude's six replicated scenario curves were monotonic and had total reversal mass 0. GPT reversed in four scenarios, with total reversal mass 1.333 and a largest adjacent drop of 0.333. GPT's aggregate curve is monotonic after pooling scenarios, so an aggregate S50 alone would hide the inconsistency. This is the strongest evidence for adding reversal mass as a primary benchmark output."
                ),
            },
            {"id": "reversal_mass", "type": "chart", "chartId": "reversal_mass_chart"},
            {"id": "scenario_detail", "type": "table", "tableId": "scenario_detail_table"},
            {
                "id": "independent_slice",
                "type": "markdown",
                "sourceId": "confirmatory_summary",
                "body": (
                    "## The new responses point the same way, with wider coherence uncertainty\n\n"
                    "Using only the 144 newly generated responses, Claude's S50 is 4 and GPT's is 8. Claude has five monotonic scenarios and mean reversal mass 0.083; GPT has three and mean reversal mass 0.250. The new-only paired bootstrap keeps the sensitivity gap above zero in every resample, while the reversal-mass interval is 0–0.333 and the difference is positive in 91.0% of resamples. This directional agreement reduces concern that the combined result is solely inherited from the pilot, but it does not replace a larger clean holdout."
                ),
            },
            {"id": "phase_comparison", "type": "table", "tableId": "phase_comparison_table"},
            {
                "id": "scope_definitions",
                "type": "markdown",
                "sourceId": "replication_plan",
                "body": (
                    "## Scope, data, and metric definitions\n\n"
                    "- **Scope:** Module A controlled odds; two target models; six scenario families; six surprisal levels; three one-shot responses per model–prompt cell.\n"
                    "- **Surprisal:** −log₁₀(p); 8 corresponds to nominal odds of 1 in 10⁸ under the stated random mechanism.\n"
                    "- **Any challenge:** automated consensus level 1 or 2. **Soft challenge:** level 1. **Explicit challenge:** level 2.\n"
                    "- **Empirical S50:** first tested surprisal with an aggregate challenge rate of at least 50%; no psychometric curve is fitted.\n"
                    "- **Reversal mass:** the sum of every positive adjacent decrease in a scenario's replicated challenge rate. Zero is perfectly monotonic in the observed levels.\n"
                    "- **Confirmatory sample:** the pre-specified three-response analysis combines one frozen pilot response with two newly generated responses per cell."
                ),
            },
            {
                "id": "methodology",
                "type": "markdown",
                "sourceId": "replication_plan",
                "body": (
                    "## Experimental design and methodology\n\n"
                    "The hypotheses, metrics, decision rules, model identifiers, grader ensemble, generation settings, bootstrap seed, and stopping rules were written to `REPLICATION_PLAN.md` and hashed before paid replication generation. Inspect generated two additional independent one-shot completions per prompt with hidden reasoning disabled and an 800-token ceiling. All 144 new responses completed normally with no errors, truncation, or attached scores.\n\n"
                    "Three frozen LLM graders labelled each response at temperature 0 and seed 42. The ordinal median sets challenge level and tag majorities set diagnostics. Wilson intervals quantify per-level binomial uncertainty. A 10,000-draw paired scenario-cluster bootstrap resamples the six scenario families while preserving each family across target models."
                ),
            },
            {
                "id": "grader_validation",
                "type": "markdown",
                "sourceId": "scoring_summary",
                "body": (
                    "## Automated scoring remained stable enough for the model comparison\n\n"
                    "The graders were unanimous on 169 of 216 responses (78.2%), reached a two-of-three majority on 46, and produced one three-way split. Pairwise exact agreement ranged from 84.7% to 86.6%. All graders place Claude's S50 at 4; GPT's grader-specific S50 ranges from 6 to 10, so the target-model ordering is invariant even though GPT's exact crossing remains grader-sensitive. A pre-selected Qwen sensitivity adjudicator matched the frozen median on the single three-way split; the primary label was not changed."
                ),
            },
            {"id": "grader_s50", "type": "chart", "chartId": "grader_s50_chart"},
            {"id": "grader_agreement", "type": "table", "tableId": "grader_agreement_table"},
            {
                "id": "limitations",
                "type": "markdown",
                "body": (
                    "## Limitations, uncertainty, and robustness\n\n"
                    "- **The primary analysis reuses exploratory data.** One-third of each cell is the pilot response that motivated the coherence hypothesis, so the combined result is pre-registered but not a fully independent holdout.\n"
                    "- **The independent slice is small.** The two new responses per cell reproduce the direction of both effects, but the new-only reversal-mass interval includes zero.\n"
                    "- **Only six scenario families are resampled.** Bootstrap intervals measure sensitivity to these scenarios, not generalization to all testimony domains.\n"
                    "- **A response-level rate is still coarse.** Three repetitions allow rates of only 0, ⅓, ⅔, or 1 within a scenario-level cell.\n"
                    "- **Automated agreement is internal reliability.** It does not establish equivalence to human epistemic judgments; no human scoring was used or is required by the benchmark.\n"
                    "- **Provider and wording scope remains narrow.** Results cover two routed models, first-person controlled-odds prompts, and one-shot conversations only."
                ),
            },
            {
                "id": "next_steps",
                "type": "markdown",
                "body": (
                    "## Recommended next steps\n\n"
                    "1. **Freeze sensitivity plus coherence as the two primary benchmark outputs.** Keep empirical S50, reversal mass, monotonic-scenario count, and explicit-challenge rate separate rather than collapsing them into one leaderboard score.\n"
                    "2. **Run a clean holdout before making a strong literature claim.** Use new controlled-odds scenario families or paraphrase families not used to discover the metric, with at least three responses per cell.\n"
                    "3. **Then run Module B separately.** Preserve implicit odds as a validation study and do not pool its empirical event rates with Module A.\n"
                    "4. **Keep grader sensitivity visible.** GPT's exact S50 varies from 6 to 10 across graders even though all preserve the model ordering."
                ),
            },
            {
                "id": "further_questions",
                "type": "markdown",
                "body": (
                    "## Further questions\n\n"
                    "- Does reversal mass persist on unseen controlled-odds stories, or is it tied to these six scenario framings?\n"
                    "- Are reversals driven by response-style stochasticity, domain priors, or inconsistent use of the stated random mechanism?\n"
                    "- Does sequential escalation increase coherence by making the evidence accumulation more salient, or decrease it through conversational accommodation?\n"
                    "- Do implicit real-world odds preserve the sensitivity ordering once source credibility and base-rate uncertainty enter the task?"
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
                "reversal_mass": reversal_mass,
                "scenario_detail": scenario_detail,
                "phase_comparison": phase_comparison,
                "grader_s50": grader_s50,
                "pairwise_agreement": pairwise_agreement,
            },
        },
        "sources": sources,
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
