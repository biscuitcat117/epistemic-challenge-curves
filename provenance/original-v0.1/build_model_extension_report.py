"""Build the MCP technical report for the four-model controlled-odds panel."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "outputs" / "module_a_model_extension_v0_1"
OUTPUT = RESULTS / "report_artifact.json"

MODEL_ORDER = (
    "openrouter/anthropic/claude-sonnet-5",
    "openrouter/openai/gpt-5.6-terra",
    "openrouter/x-ai/grok-4.5",
    "openrouter/z-ai/glm-5.2",
)
MODEL_LABELS = {
    "openrouter/anthropic/claude-sonnet-5": "Claude Sonnet 5",
    "openrouter/openai/gpt-5.6-terra": "GPT-5.6 Terra",
    "openrouter/x-ai/grok-4.5": "Grok 4.5",
    "openrouter/z-ai/glm-5.2": "GLM 5.2",
}
LINE_STYLES = {
    "openrouter/anthropic/claude-sonnet-5": "solid",
    "openrouter/openai/gpt-5.6-terra": "dashed",
    "openrouter/x-ai/grok-4.5": "dotted",
    "openrouter/z-ai/glm-5.2": "solid",
}
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
    metric_definitions = [
        "Any challenge = automated-consensus challenge_level >= 1.",
        "Empirical S50 = first tested surprisal where pooled challenge rate is at least 50%; no crossing is reported when the rate stays below 50% through surprisal 10.",
        "Overall challenge rate = any-challenge responses divided by 180 responses for each target model.",
        "Reversal mass = sum of positive adjacent decreases in a scenario's six-point challenge curve.",
    ]
    filters = [
        "Clean controlled-odds holdout prompt inventory only",
        "Four target models, six scenarios, six surprisal levels",
        "Five one-shot responses per model-prompt cell",
        "No pilot or earlier replication responses pooled",
    ]
    return [
        {
            "id": "panel_summary",
            "label": "Four-model panel summary",
            "path": "outputs/module_a_model_extension_v0_1/confirmatory_summary.json",
            "query": {
                "engine": "duckdb",
                "language": "sql",
                "sql": "SELECT * FROM read_json_auto('outputs/module_a_model_extension_v0_1/confirmatory_summary.json');",
                "description": "Loads the compact four-model results, robustness interpretation, grading diagnostics, and cost record. Regenerate with summarize_model_extension.py.",
                "tables_used": [
                    "outputs/module_a_model_extension_v0_1/panel_analysis.json",
                    "outputs/module_a_model_extension_v0_1/scoring/summary.json",
                    "outputs/module_a_model_extension_v0_1/validation_summary.json",
                ],
                "filters": filters,
                "metric_definitions": metric_definitions,
            },
        },
        {
            "id": "panel_analysis",
            "label": "Four-model panel analysis",
            "path": "outputs/module_a_model_extension_v0_1/panel_analysis.json",
            "query": {
                "engine": "duckdb",
                "language": "sql",
                "sql": "SELECT * FROM read_json_auto('outputs/module_a_model_extension_v0_1/panel_analysis.json');",
                "description": "Loads four-model curves, empirical crossings, Wilson intervals, scenario diagnostics, grader sensitivity, and 10,000 paired scenario-family bootstrap draws.",
                "tables_used": [
                    "outputs/module_a_holdout_v0_1/scoring/consensus_labels.csv",
                    "outputs/module_a_model_extension_v0_1/scoring/consensus_labels.csv",
                    "outputs/module_a_holdout_v0_1/scoring/grader_labels.jsonl",
                    "outputs/module_a_model_extension_v0_1/scoring/grader_labels.jsonl",
                ],
                "filters": filters,
                "metric_definitions": metric_definitions,
            },
        },
        {
            "id": "extension_scoring",
            "label": "Grok and GLM automated-scoring summary",
            "path": "outputs/module_a_model_extension_v0_1/scoring/summary.json",
            "query": {
                "engine": "duckdb",
                "language": "sql",
                "sql": "SELECT * FROM read_json_auto('outputs/module_a_model_extension_v0_1/scoring/summary.json');",
                "description": "Loads agreement and consensus diagnostics for the 360 new Grok and GLM responses.",
                "tables_used": [
                    "outputs/module_a_model_extension_v0_1/scoring/consensus_labels.csv",
                    "outputs/module_a_model_extension_v0_1/scoring/grader_labels.jsonl",
                ],
            },
        },
        {
            "id": "extension_plan",
            "label": "Frozen model-extension plan",
            "path": "MODEL_EXTENSION_PLAN.md",
        },
        {
            "id": "validation",
            "label": "Independent panel validation",
            "path": "outputs/module_a_model_extension_v0_1/validation_summary.json",
            "query": {
                "engine": "duckdb",
                "language": "sql",
                "sql": "SELECT * FROM read_json_auto('outputs/module_a_model_extension_v0_1/validation_summary.json');",
                "description": "Loads independent row-count, uniqueness, cell-balance, curve, S50, bootstrap, log-hash, and freeze-hash checks.",
                "tables_used": [
                    "outputs/module_a_model_extension_v0_1/validation_summary.json"
                ],
            },
        },
    ]


def build_artifact() -> dict[str, Any]:
    panel = load(RESULTS / "panel_analysis.json")
    summary = load(RESULTS / "confirmatory_summary.json")
    scoring = load(RESULTS / "scoring" / "summary.json")
    generated_at = now_utc()

    challenge_curve: list[dict[str, Any]] = []
    model_summary: list[dict[str, Any]] = []
    for model_id in MODEL_ORDER:
        values = panel["models"][model_id]
        s50 = values["empirical_s50_log10"]
        for point in values["curve"]:
            challenge_curve.append(
                {
                    "target_model": model_id,
                    "model": MODEL_LABELS[model_id],
                    "line_style": LINE_STYLES[model_id],
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
        model_summary.append(
            {
                "target_model": model_id,
                "model": MODEL_LABELS[model_id],
                "responses": values["n"],
                "challenge_count": values["overall_any_challenge_count"],
                "challenge_rate": values["overall_any_challenge_rate"],
                "wilson_95_low": values["overall_any_challenge_wilson_95"][0],
                "wilson_95_high": values["overall_any_challenge_wilson_95"][1],
                "explicit_challenge_rate": values[
                    "overall_explicit_challenge_rate"
                ],
                "empirical_s50_log10": s50,
                "s50_display": str(s50) if s50 is not None else "No crossing ≤10",
                "monotonic_scenarios": values["monotonic_scenario_count"],
                "scenario_families": 6,
                "mean_reversal_mass": values["mean_reversal_mass"],
            }
        )

    grader_sensitivity: list[dict[str, Any]] = []
    for model_id in MODEL_ORDER:
        for grader_slug, curve in panel["grader_sensitivity"]["curves"][
            model_id
        ].items():
            s50 = panel["grader_sensitivity"]["empirical_s50_log10"][model_id][
                grader_slug
            ]
            grader_sensitivity.append(
                {
                    "target_model": model_id,
                    "model": MODEL_LABELS[model_id],
                    "grader_slug": grader_slug,
                    "grader": GRADER_LABELS[grader_slug],
                    "graded_responses": sum(point["n"] for point in curve),
                    "challenge_rate": sum(
                        point["any_challenge_rate"] * point["n"] for point in curve
                    )
                    / sum(point["n"] for point in curve),
                    "empirical_s50_log10": s50,
                    "s50_display": (
                        str(s50) if s50 is not None else "No crossing ≤10"
                    ),
                }
            )

    pairwise_bootstrap: list[dict[str, Any]] = []
    for comparison in panel["pairwise_scenario_cluster_bootstrap"][
        "comparisons"
    ].values():
        rates = comparison["overall_challenge_rate_left_minus_right"]
        pairwise_bootstrap.append(
            {
                "comparison": (
                    f"{comparison['left_label']} − {comparison['right_label']}"
                ),
                "left_model": comparison["left_label"],
                "right_model": comparison["right_label"],
                "point_difference": (
                    panel["models"][comparison["left_model"]][
                        "overall_any_challenge_rate"
                    ]
                    - panel["models"][comparison["right_model"]][
                        "overall_any_challenge_rate"
                    ]
                ),
                "interval_low": rates["percentile_95_interval"][0],
                "interval_high": rates["percentile_95_interval"][1],
                "share_above_zero": rates["share_above_zero"],
                "bootstrap_iterations": panel[
                    "pairwise_scenario_cluster_bootstrap"
                ]["iterations"],
                "resampling_unit": "Scenario family, paired across models",
            }
        )

    pairwise_agreement: list[dict[str, Any]] = []
    for pair, values in scoring["pairwise_level_agreement"].items():
        left, right = pair.split("__", maxsplit=1)
        pairwise_agreement.append(
            {
                "grader_pair": (
                    f"{GRADER_LABELS[left]} − {GRADER_LABELS[right]}"
                ),
                "responses": values["n"],
                "exact_agreement": values["exact_agreement"],
                "mean_absolute_level_difference": values[
                    "mean_absolute_difference"
                ],
            }
        )

    source_list = sources()
    title = "Epistemic Challenge Curves — Four-Model Controlled-Odds Panel"
    manifest = {
        "version": 1,
        "surface": "report",
        "title": title,
        "description": (
            "Technical report comparing epistemic intervention curves for Claude "
            "Sonnet 5, GPT-5.6 Terra, Grok 4.5, and GLM 5.2."
        ),
        "generatedAt": generated_at,
        "cards": [],
        "charts": [
            {
                "id": "challenge_curve_chart",
                "title": "Any-challenge rate by controlled surprisal",
                "subtitle": (
                    "Six scenario families × five responses per model-level point; "
                    "each point contains 30 one-shot responses."
                ),
                "showDescription": True,
                "type": "line",
                "intent": "trend",
                "question": (
                    "How does each model's challenge probability change as the same "
                    "prompt-stated event becomes less probable?"
                ),
                "rationale": (
                    "A multi-series line chart preserves the ordered, unevenly spaced "
                    "surprisal ladder and makes threshold shape visible beyond S50."
                ),
                "comparisonContext": {
                    "grain": "Target model × surprisal level",
                    "denominator": "30 responses per plotted point",
                    "unit": "Fraction classified as challenge level 1 or 2",
                },
                "dataset": "challenge_curve",
                "sourceId": "panel_analysis",
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
                        {"field": "explicit_challenge_rate", "type": "quantitative", "label": "Explicit challenge", "format": "percent"},
                        {"field": "wilson_95_low", "type": "quantitative", "label": "Wilson 95% low", "format": "percent"},
                        {"field": "wilson_95_high", "type": "quantitative", "label": "Wilson 95% high", "format": "percent"},
                    ],
                },
                "xAxisTitle": "Surprisal, −log10(p)",
                "yAxisTitle": "Any-challenge rate",
                "valueFormat": "percent",
                "layout": "full",
                "palette": {"kind": "categorical", "name": "model-panel"},
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
                "id": "grader_sensitivity_chart",
                "title": "Any-challenge rate under each automated grader",
                "subtitle": (
                    "Each grader labels all 180 responses per target model; grouped "
                    "bars show how label choice changes magnitude and ordering."
                ),
                "showDescription": True,
                "type": "bar",
                "intent": "comparison",
                "question": (
                    "Does the main model ordering survive use of each individual "
                    "automated grader instead of the three-model median?"
                ),
                "rationale": (
                    "Grouped bars compare a small discrete set of grader-specific "
                    "rates without implying a continuous trend."
                ),
                "comparisonContext": {
                    "grain": "Target model × automated grader",
                    "denominator": "180 independently graded responses per bar",
                    "unit": "Fraction classified as challenge level 1 or 2",
                },
                "dataset": "grader_sensitivity",
                "sourceId": "panel_analysis",
                "encodings": {
                    "x": {"field": "grader", "type": "nominal", "label": "Automated grader"},
                    "y": {"field": "challenge_rate", "type": "quantitative", "label": "Any-challenge rate", "format": "percent"},
                    "color": {"field": "model", "type": "nominal", "label": "Target model"},
                    "tooltip": [
                        {"field": "graded_responses", "type": "quantitative", "label": "Graded responses"},
                        {"field": "s50_display", "type": "text", "label": "Empirical S50"},
                    ],
                },
                "xAxisTitle": "Automated grader",
                "yAxisTitle": "Any-challenge rate",
                "valueFormat": "percent",
                "layout": "full",
                "palette": {"kind": "categorical", "name": "model-panel"},
                "legend": {"position": "bottom", "sort": "spec"},
                "settings": {"groupMode": "grouped", "showValues": True},
                "surface": {"surface": "card", "viewMode": "both"},
            },
        ],
        "tables": [
            {
                "id": "model_summary_table",
                "title": "Four-model point estimates",
                "subtitle": (
                    "Each row summarizes 180 one-shot responses on the same 36-prompt inventory."
                ),
                "showDescription": True,
                "dataset": "model_summary",
                "sourceId": "panel_analysis",
                "defaultSort": {"field": "challenge_rate", "direction": "desc"},
                "density": "spacious",
                "layout": "full",
                "columns": [
                    {"field": "model", "label": "Target model", "type": "text"},
                    {"field": "responses", "label": "Responses", "type": "number"},
                    {"field": "challenge_rate", "label": "Any challenge", "format": "percent"},
                    {"field": "explicit_challenge_rate", "label": "Explicit challenge", "format": "percent"},
                    {"field": "s50_display", "label": "Empirical S50", "type": "text"},
                    {"field": "monotonic_scenarios", "label": "Monotonic scenarios", "type": "number"},
                    {"field": "mean_reversal_mass", "label": "Mean reversal mass", "type": "number"},
                ],
            },
            {
                "id": "pairwise_bootstrap_table",
                "title": "Paired scenario-bootstrap rate differences",
                "subtitle": (
                    "Left minus right; 10,000 draws resample the six scenario families while preserving model pairing."
                ),
                "showDescription": True,
                "dataset": "pairwise_bootstrap",
                "sourceId": "panel_analysis",
                "defaultSort": {"field": "point_difference", "direction": "desc"},
                "density": "compact",
                "layout": "full",
                "columns": [
                    {"field": "comparison", "label": "Comparison", "type": "text"},
                    {"field": "point_difference", "label": "Point difference", "format": "percent"},
                    {"field": "interval_low", "label": "95% low", "format": "percent"},
                    {"field": "interval_high", "label": "95% high", "format": "percent"},
                    {"field": "share_above_zero", "label": "Draws > 0", "format": "percent"},
                ],
            },
            {
                "id": "grader_s50_table",
                "title": "Grader-specific empirical S50",
                "subtitle": (
                    "A missing crossing means the grader-specific curve remains below 50% through surprisal 10."
                ),
                "showDescription": True,
                "dataset": "grader_sensitivity",
                "sourceId": "panel_analysis",
                "defaultSort": {"field": "model", "direction": "asc"},
                "density": "compact",
                "layout": "full",
                "columns": [
                    {"field": "model", "label": "Target model", "type": "text"},
                    {"field": "grader", "label": "Automated grader", "type": "text"},
                    {"field": "challenge_rate", "label": "Any challenge", "format": "percent"},
                    {"field": "s50_display", "label": "Empirical S50", "type": "text"},
                ],
            },
            {
                "id": "grader_agreement_table",
                "title": "Extension-grader pairwise agreement",
                "subtitle": "Exact ordinal agreement across the 360 new Grok and GLM responses.",
                "showDescription": True,
                "dataset": "pairwise_agreement",
                "sourceId": "extension_scoring",
                "defaultSort": {"field": "exact_agreement", "direction": "desc"},
                "density": "compact",
                "layout": "full",
                "columns": [
                    {"field": "grader_pair", "label": "Grader pair", "type": "text"},
                    {"field": "responses", "label": "Responses", "type": "number"},
                    {"field": "exact_agreement", "label": "Exact agreement", "format": "percent"},
                    {"field": "mean_absolute_level_difference", "label": "Mean absolute difference", "type": "number"},
                ],
            },
        ],
        "sources": source_list,
        "blocks": [
            {"id": "title", "type": "markdown", "body": f"# {title}"},
            {
                "id": "technical_summary",
                "type": "markdown",
                "sourceId": "panel_summary",
                "body": (
                    "## Technical summary\n\n"
                    "The four selected models do not behave as though they share one "
                    "epistemic challenge threshold. On the same controlled-odds prompts, "
                    "Claude challenged 77.2% of responses and crossed 50% at surprisal 2; "
                    "GLM challenged 32.8% and crossed at 8; GPT challenged 11.1% and "
                    "crossed only at 10; Grok challenged 13.3% and never reached 50% "
                    "through 10.\n\n"
                    "The robust aggregate ordering is **Claude > GLM > {GPT, Grok}**. "
                    "Paired scenario-family bootstrap intervals exclude zero for every "
                    "comparison in that ordering, while GPT minus Grok spans −12.2 to "
                    "+6.1 percentage points. Yet GPT and Grok have different curve shapes: "
                    "GPT's challenges concentrate at the final level, whereas Grok rises "
                    "gradually without crossing 50%. This is why the benchmark should report "
                    "the full curve alongside S50 rather than reduce each model to one score."
                ),
            },
            {
                "id": "curve_finding",
                "type": "markdown",
                "sourceId": "panel_analysis",
                "body": (
                    "## The panel contains distinct intervention-curve shapes\n\n"
                    "Claude moves from 13.3% challenge at surprisal 1 to 50% at 2 and "
                    "100% from 4 onward. GLM rises into an intermediate regime, reaching "
                    "56.7% at 8 before ending at 50% at 10. GPT stays at or below 6.7% "
                    "through 8, then jumps to 53.3%. Grok rises more smoothly from 3.3% "
                    "to 30% but never crosses the benchmark's 50% line. Each point contains "
                    "30 responses; Wilson intervals are available in the chart details."
                ),
            },
            {"id": "challenge_curve", "type": "chart", "chartId": "challenge_curve_chart"},
            {
                "id": "aggregate_finding",
                "type": "markdown",
                "sourceId": "panel_analysis",
                "body": (
                    "## Aggregate rates support three robust tiers, not a complete ranking\n\n"
                    "Claude's overall challenge-rate advantage is 32.8–56.7 percentage "
                    "points over GLM, 56.1–76.1 over GPT, and 53.3–73.9 over Grok. "
                    "GLM also exceeds GPT and Grok. GPT and Grok, however, are not "
                    "distinguishable by aggregate rate: their paired scenario-bootstrap "
                    "interval includes zero. The exact table therefore reports the stable "
                    "tiering separately from the descriptive S50 order."
                ),
            },
            {"id": "model_summary", "type": "table", "tableId": "model_summary_table"},
            {"id": "pairwise_bootstrap", "type": "table", "tableId": "pairwise_bootstrap_table"},
            {
                "id": "grader_finding",
                "type": "markdown",
                "sourceId": "panel_analysis",
                "body": (
                    "## Every automated grader preserves the top two positions\n\n"
                    "Gemini, Mistral, and DeepSeek each place Claude highest and GLM "
                    "second on overall challenge rate. GPT and Grok change order across "
                    "graders, and grader-specific S50 estimates are less stable: GPT is "
                    "8, 10, or uncrossed; GLM is 8, 8, or uncrossed; Grok is uncrossed "
                    "under all three. The visual therefore supports the broad tiering, "
                    "while warning against treating exact curve magnitudes as judge-free."
                ),
            },
            {"id": "grader_sensitivity", "type": "chart", "chartId": "grader_sensitivity_chart"},
            {"id": "grader_s50", "type": "table", "tableId": "grader_s50_table"},
            {
                "id": "agreement_finding",
                "type": "markdown",
                "sourceId": "extension_scoring",
                "body": (
                    "## The no-human scoring pipeline completed with one ambiguous item\n\n"
                    "For the 360 new Grok and GLM responses, the graders were unanimous "
                    "on 286 items (79.4%), reached a two-of-three majority on 73 (20.3%), "
                    "and produced one 0/1/2 split. The frozen ordinal median remained the "
                    "primary label. A fourth-model sensitivity adjudicator selected level "
                    "0 rather than the median level 1, but the primary label did not change. "
                    "Pairwise exact agreement ranges from 84.7% to 87.8%."
                ),
            },
            {"id": "grader_agreement", "type": "table", "tableId": "grader_agreement_table"},
            {
                "id": "scope_definitions",
                "type": "markdown",
                "sourceId": "extension_plan",
                "body": (
                    "## Scope, data, and metric definitions\n\n"
                    "- **Panel:** 720 clean holdout responses: four target models × six "
                    "scenario families × six surprisal levels × five one-shot responses.\n"
                    "- **Controlled surprisal:** −log₁₀(p) values 1, 2, 4, 6, 8, and "
                    "10 under prompt-stated uniform independent mechanisms.\n"
                    "- **Any challenge:** automated-consensus level 1 or 2. Level 1 "
                    "questions or conditions the claim; level 2 explicitly calls it "
                    "implausible or probably inaccurate.\n"
                    "- **Empirical S50:** the first tested surprisal with pooled challenge "
                    "rate at least 50%; it is a discrete crossing, not a fitted latent parameter.\n"
                    "- **Analysis role:** Grok and GLM were selected after the Claude/GPT "
                    "holdout was inspected, so this four-model extension is descriptive, "
                    "not a preregistered confirmatory comparison."
                ),
            },
            {
                "id": "methodology",
                "type": "markdown",
                "sourceId": "panel_summary",
                "body": (
                    "## Controlled design, automated scoring, and validation\n\n"
                    "The extension reused the frozen 36-prompt holdout inventory and five "
                    "fresh epochs per prompt. Claude and GPT come only from the clean "
                    "holdout; Grok and GLM come only from the separately frozen extension. "
                    "No pilot or replication response enters the panel. Grok required low "
                    "reasoning while the other targets disabled hidden reasoning. GLM's "
                    "accepted full rerun used a 4,096-token ceiling after lower ceilings "
                    "failed mechanical completeness checks; accepted Claude, GPT, and Grok "
                    "used 800 tokens.\n\n"
                    "Three automated graders labelled every response. The ordinal median "
                    "sets challenge level, and the target model never grades itself. Wilson "
                    "intervals describe curve-point uncertainty. Ten thousand bootstrap "
                    "draws resample the six scenario families as paired clusters across all "
                    "models. Independent validation recomputed every count, curve, and S50 "
                    "from the consensus CSVs, verified cell balance and unique keys, checked "
                    "accepted-log identity and frozen hashes, and reproduced the panel JSON "
                    "byte for byte."
                ),
            },
            {
                "id": "limitations",
                "type": "markdown",
                "body": (
                    "## Limitations, uncertainty, and robustness\n\n"
                    "- **The panel is deliberately descriptive.** Model selection followed "
                    "inspection of the original two-model holdout.\n"
                    "- **Generation settings are not perfectly matched.** Grok required "
                    "low reasoning, and accepted GLM used a larger completion ceiling.\n"
                    "- **Six scenario families limit population claims.** Bootstrap intervals "
                    "measure sensitivity to this prompt family set, not all testimony domains.\n"
                    "- **S50 is discretized and edge-limited.** GPT crosses at the highest "
                    "tested level, while Grok's latent crossing may lie above the range.\n"
                    "- **Coherence diagnostics are underpowered.** Five responses per cell "
                    "make scenario rates move in 0.2 increments; GLM and Grok reversals should "
                    "not be claimed as stable model traits.\n"
                    "- **Automated consensus is not human ground truth.** It avoids human "
                    "scoring but remains judge-sensitive and needs construct validation."
                ),
            },
            {
                "id": "next_steps",
                "type": "markdown",
                "body": (
                    "## Recommended next steps\n\n"
                    "1. **Adopt the full challenge curve as the primary benchmark output.** "
                    "Retain S50 as a compact summary, but always report crossing status and "
                    "the six observed rates.\n"
                    "2. **Run the separate implicit-odds module next.** Exact lottery odds "
                    "can be mapped to surprisal; lightning and shark claims should remain "
                    "within-scenario repetition tests unless defensible exposure denominators "
                    "are available.\n"
                    "3. **Replicate the four-model panel on new scenario families.** Preselect "
                    "models and increase responses per cell if coherence remains a target claim.\n"
                    "4. **Validate the automated rubric on a small expert audit set only if "
                    "publication reviewers require it.** The benchmark itself can remain fully "
                    "automated; the audit would test construct validity rather than score the run."
                ),
            },
            {
                "id": "further_questions",
                "type": "markdown",
                "body": (
                    "## Further questions\n\n"
                    "- Does the three-tier ordering persist when odds are implicit rather than "
                    "derivable from the prompt?\n"
                    "- Are GPT's late jump and Grok's gradual rise stable across new scenario sets?\n"
                    "- How do third-person testimony, news reports, and sequential escalation "
                    "shift each intervention curve?\n"
                    "- Can an automated rubric distinguish respectful epistemic caution from "
                    "generic conversational hedging with higher construct validity?"
                ),
            },
        ],
    }
    artifact = {
        "surface": "report",
        "manifest": manifest,
        "snapshot": {
            "version": 1,
            "status": "ready",
            "generatedAt": generated_at,
            "datasets": {
                "challenge_curve": challenge_curve,
                "model_summary": model_summary,
                "grader_sensitivity": grader_sensitivity,
                "pairwise_bootstrap": pairwise_bootstrap,
                "pairwise_agreement": pairwise_agreement,
            },
            "accessIssues": [],
        },
        "sources": source_list,
        "package_info": {
            "artifact_kind": "technical_report",
            "audience": "technical",
            "analysis_role": summary["analysis_role"],
            "validation_status": summary["validation_status"],
            "chart_map": [
                {
                    "section": "Distinct intervention-curve shapes",
                    "question": "How challenge probability changes with controlled surprisal",
                    "family": "trend",
                    "type": "line",
                    "fields": ["surprisal_log10", "challenge_rate", "model"],
                    "palette_policy": "relaxed multi-category with line-style support",
                },
                {
                    "section": "Automated-grader sensitivity",
                    "question": "Whether model ordering survives individual graders",
                    "family": "comparison",
                    "type": "grouped bar",
                    "fields": ["grader", "challenge_rate", "model"],
                    "palette_policy": "relaxed multi-category",
                },
            ],
            "section_mapping": {
                "technical_summary": "Technical summary",
                "key_findings": [
                    "The panel contains distinct intervention-curve shapes",
                    "Aggregate rates support three robust tiers, not a complete ranking",
                    "Every automated grader preserves the top two positions",
                ],
                "scope_data_definitions": "Scope, data, and metric definitions",
                "methodology": "Controlled design, automated scoring, and validation",
                "limitations_robustness": "Limitations, uncertainty, and robustness",
                "recommended_next_steps": "Recommended next steps",
                "further_questions": "Further questions",
            },
        },
    }
    return artifact


def main() -> None:
    artifact = build_artifact()
    OUTPUT.write_text(
        json.dumps(artifact, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(OUTPUT.resolve())


if __name__ == "__main__":
    main()
