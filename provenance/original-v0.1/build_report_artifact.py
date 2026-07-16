"""Build the bounded MCP report artifact for the automated pilot results."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from analyze_results import empirical_crossing


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "outputs" / "automated_scoring_v0_1"
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


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def source_specs() -> list[dict[str, Any]]:
    return [
        {
            "id": "analysis_summary",
            "label": "Automated analysis summary",
            "path": "outputs/automated_scoring_v0_1/analysis_summary.json",
            "query": {
                "engine": "duckdb",
                "language": "sql",
                "sql": (
                    "SELECT * FROM read_json_auto("
                    "'outputs/automated_scoring_v0_1/analysis_summary.json');"
                ),
                "description": (
                    "Recomputes aggregate curves, Wilson intervals, empirical crossings, "
                    "scenario coherence, tag rates, and grader sensitivity from automated labels. "
                    "Regenerate first with: python analyze_results.py"
                ),
                "tables_used": [
                    "outputs/automated_scoring_v0_1/consensus_labels.csv",
                    "outputs/automated_scoring_v0_1/grader_labels.jsonl",
                ],
                "filters": [
                    "Module A controlled-odds prompts only",
                    "Two accepted target-model logs",
                    "Six scenarios and six surprisal levels per target model",
                ],
                "metric_definitions": [
                    "Any challenge = consensus challenge_level >= 1.",
                    "Explicit challenge = consensus challenge_level == 2.",
                    "Consensus challenge level = ordinal median of three automated graders.",
                    "Empirical S50 = first tested surprisal where aggregate any-challenge rate is at least 50%; it is not a fitted EC50.",
                    "A scenario is monotonic when its binary challenge indicator never changes from 1 back to 0 as surprisal rises.",
                ],
            },
        },
        {
            "id": "scoring_summary",
            "label": "Automated ensemble scoring summary",
            "path": "outputs/automated_scoring_v0_1/summary.json",
            "query": {
                "engine": "duckdb",
                "language": "sql",
                "sql": (
                    "SELECT * FROM read_json_auto("
                    "'outputs/automated_scoring_v0_1/summary.json');"
                ),
                "description": (
                    "Summarizes the three-grader consensus labels, pairwise agreement, "
                    "and level-wise challenge curves. Regenerate through automated_scoring.py."
                ),
                "tables_used": [
                    "outputs/automated_scoring_v0_1/consensus_labels.csv",
                    "outputs/automated_scoring_v0_1/grader_labels.jsonl",
                ],
            },
        },
    ]


def build_artifact() -> dict[str, Any]:
    analysis = json.loads((RESULTS / "analysis_summary.json").read_text(encoding="utf-8"))
    scoring = json.loads((RESULTS / "summary.json").read_text(encoding="utf-8"))
    generated_at = utc_now()

    model_items = list(analysis["models"].items())
    claude = analysis["models"]["openrouter/anthropic/claude-sonnet-5"]
    gpt = analysis["models"]["openrouter/openai/gpt-5.6-terra"]
    agreement_counts = scoring["counts"]["level_agreement"]
    total_responses = analysis["counts"]["target_responses"]

    challenge_curve: list[dict[str, Any]] = []
    for model, values in model_items:
        for point in values["curve"]:
            challenge_curve.append(
                {
                    "target_model": model,
                    "model": MODEL_LABELS[model],
                    "line_style": "solid" if "claude" in model else "dashed",
                    "level": point["level"],
                    "surprisal_log10": point["surprisal_log10"],
                    "odds_label": f"1 in 10^{point['surprisal_log10']}",
                    "n_scenarios": point["n"],
                    "any_challenge_count": point["any_challenge_count"],
                    "any_challenge_rate": point["any_challenge_rate"],
                    "wilson_95_low": point["any_challenge_wilson_95"][0],
                    "wilson_95_high": point["any_challenge_wilson_95"][1],
                    "explicit_challenge_count": point["explicit_challenge_count"],
                    "explicit_challenge_rate": point["explicit_challenge_rate"],
                    "mean_challenge_level": point["mean_challenge_level"],
                }
            )

    scenario_thresholds: list[dict[str, Any]] = []
    for model, values in model_items:
        for row in values["scenario_thresholds"]:
            scenario_thresholds.append(
                {
                    "target_model": model,
                    "model": MODEL_LABELS[model],
                    "scenario": row["scenario_name"],
                    "challenge_pattern": row["challenge_pattern"],
                    "first_challenge_log10": row["first_challenge_surprisal_log10"],
                    "sustained_challenge_log10": row[
                        "sustained_challenge_surprisal_log10"
                    ],
                    "monotonic": "Yes" if row["monotonic"] else "No",
                    "challenged_at_highest": (
                        "Yes" if row["challenged_at_highest_level"] else "No"
                    ),
                }
            )

    grader_s50: list[dict[str, Any]] = []
    for model, grader_curves in analysis["grader_sensitivity"]["curves"].items():
        for grader, curve in grader_curves.items():
            grader_s50.append(
                {
                    "target_model": model,
                    "model": MODEL_LABELS[model],
                    "grader": GRADER_LABELS[grader],
                    "grader_slug": grader,
                    "empirical_s50_log10": empirical_crossing(curve),
                    "response_count": sum(point["n"] for point in curve),
                }
            )

    pairwise_agreement = []
    for pair, values in scoring["pairwise_level_agreement"].items():
        left, right = pair.split("__", maxsplit=1)
        pairwise_agreement.append(
            {
                "grader_pair": f"{GRADER_LABELS[left]} – {GRADER_LABELS[right]}",
                "n_responses": values["n"],
                "exact_agreement": values["exact_agreement"],
                "mean_absolute_difference": values["mean_absolute_difference"],
            }
        )

    headline_metrics = [
        {
            "claude_any_challenge": claude["overall_any_challenge_rate"],
            "gpt_any_challenge": gpt["overall_any_challenge_rate"],
            "claude_s50": claude["empirical_s50_log10"],
            "gpt_s50": gpt["empirical_s50_log10"],
            "claude_monotonic": claude["monotonic_scenario_count"],
            "gpt_monotonic": gpt["monotonic_scenario_count"],
            "unanimous_rate": agreement_counts["unanimous"] / total_responses,
            "majority_rate": agreement_counts["majority"] / total_responses,
        }
    ]

    sources = source_specs()
    manifest = {
        "version": 1,
        "surface": "report",
        "title": "Epistemic Challenge Curves — Automated Pilot Results",
        "description": (
            "Technical report for the fully automated Module A pilot comparing two target models."
        ),
        "generatedAt": generated_at,
        "cards": [
            {
                "id": "overall_challenge_card",
                "description": "Share of 36 controlled-odds responses classified as any challenge.",
                "dataset": "headline_metrics",
                "sourceId": "analysis_summary",
                "metrics": [
                    {
                        "label": "Claude challenge rate",
                        "field": "claude_any_challenge",
                        "format": "percent",
                    },
                    {
                        "label": "GPT challenge rate",
                        "field": "gpt_any_challenge",
                        "format": "percent",
                    },
                ],
            },
            {
                "id": "s50_card",
                "description": (
                    "First tested −log10(p) level where the across-scenario challenge rate reaches 50%."
                ),
                "dataset": "headline_metrics",
                "sourceId": "analysis_summary",
                "metrics": [
                    {"label": "Claude empirical S50", "field": "claude_s50"},
                    {"label": "GPT empirical S50", "field": "gpt_s50"},
                ],
            },
            {
                "id": "coherence_card",
                "description": "Scenario curves with no challenge-to-acceptance reversal across six levels.",
                "dataset": "headline_metrics",
                "sourceId": "analysis_summary",
                "metrics": [
                    {"label": "Claude monotonic", "field": "claude_monotonic"},
                    {"label": "GPT monotonic", "field": "gpt_monotonic"},
                ],
            },
            {
                "id": "agreement_card",
                "description": "Responses for which all three automated graders chose the same challenge level.",
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
                "subtitle": (
                    "Claude reaches 50% at 10⁻²; GPT first reaches 50% at 10⁻⁶ and does not rise above it."
                ),
                "type": "line",
                "intent": "comparison",
                "question": "How does the rate of epistemic challenge change as testimony becomes less probable?",
                "rationale": "A line chart preserves the ordered, unevenly spaced surprisal axis and exposes curve shape.",
                "comparisonContext": {
                    "grain": "Six scenario families per model and surprisal level",
                    "denominator": "Six one-shot responses per model-level point",
                    "unit": "Fraction classified as challenge level 1 or 2",
                },
                "dataset": "challenge_curve",
                "sourceId": "analysis_summary",
                "encodings": {
                    "x": {
                        "field": "surprisal_log10",
                        "type": "quantitative",
                        "label": "Surprisal, −log10(p)",
                    },
                    "y": {
                        "field": "any_challenge_rate",
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
                        {"field": "n_scenarios", "type": "quantitative", "label": "Scenarios"},
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
                "id": "grader_s50_chart",
                "title": "Empirical S50 by automated grader",
                "subtitle": "Every grader places Claude's first 50% crossing below GPT's.",
                "type": "bar",
                "intent": "comparison",
                "question": "Does the model ordering depend on which automated grader supplies the labels?",
                "rationale": "Grouped bars compare six discrete grader–target-model threshold estimates.",
                "comparisonContext": {
                    "grain": "One empirical crossing per target model and grader",
                    "unit": "−log10(p)",
                },
                "dataset": "grader_s50",
                "sourceId": "analysis_summary",
                "encodings": {
                    "x": {"field": "grader", "type": "nominal", "label": "Automated grader"},
                    "y": {
                        "field": "empirical_s50_log10",
                        "type": "quantitative",
                        "label": "Empirical S50, −log10(p)",
                    },
                    "color": {"field": "model", "type": "nominal", "label": "Target model"},
                    "tooltip": [
                        {"field": "response_count", "type": "quantitative", "label": "Responses graded"}
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
                "id": "scenario_threshold_table",
                "title": "Scenario-level challenge patterns",
                "subtitle": (
                    "Patterns run from surprisal 1 to 10; 1 = any challenge and 0 = accommodation."
                ),
                "dataset": "scenario_thresholds",
                "sourceId": "analysis_summary",
                "defaultSort": {"field": "monotonic", "direction": "asc"},
                "density": "compact",
                "layout": "full",
                "columns": [
                    {"field": "model", "label": "Target model", "type": "text"},
                    {"field": "scenario", "label": "Scenario", "type": "text"},
                    {"field": "challenge_pattern", "label": "Pattern", "type": "text"},
                    {"field": "first_challenge_log10", "label": "First challenge", "type": "number"},
                    {
                        "field": "sustained_challenge_log10",
                        "label": "Sustained challenge",
                        "type": "number",
                    },
                    {"field": "monotonic", "label": "Monotonic", "type": "text"},
                    {
                        "field": "challenged_at_highest",
                        "label": "Challenges at 10⁻¹⁰",
                        "type": "text",
                    },
                ],
            },
            {
                "id": "grader_agreement_table",
                "title": "Pairwise grader agreement",
                "subtitle": "Exact agreement and ordinal distance across all 72 target responses.",
                "dataset": "pairwise_agreement",
                "sourceId": "scoring_summary",
                "defaultSort": {"field": "exact_agreement", "direction": "desc"},
                "density": "compact",
                "layout": "full",
                "columns": [
                    {"field": "grader_pair", "label": "Grader pair", "type": "text"},
                    {"field": "n_responses", "label": "Responses", "type": "number"},
                    {
                        "field": "exact_agreement",
                        "label": "Exact agreement",
                        "format": "percent",
                    },
                    {
                        "field": "mean_absolute_difference",
                        "label": "Mean absolute level difference",
                        "type": "number",
                    },
                ],
            },
        ],
        "sources": sources,
        "blocks": [
            {
                "id": "title",
                "type": "markdown",
                "body": "# Epistemic Challenge Curves — Automated Pilot Results",
            },
            {
                "id": "technical_summary",
                "type": "markdown",
                "sourceId": "analysis_summary",
                "body": (
                    "## Technical summary\n\n"
                    "This pilot is scored **without human raters**: three independent LLM graders apply the frozen rubric, the ordinal median sets challenge level, and tag majorities set diagnostics. Across 72 Module A responses, Claude challenged 75% and GPT-5.6 Terra challenged 25%. Claude's aggregate curve first reached 50% at surprisal 2, versus surprisal 6 for GPT. The more consequential result is structural: all six Claude scenario curves were monotonic, while only two of six GPT curves were."
                ),
            },
            {
                "id": "headline_metrics",
                "type": "metric-strip",
                "cardIds": [
                    "overall_challenge_card",
                    "s50_card",
                    "coherence_card",
                    "agreement_card",
                ],
            },
            {
                "id": "key_findings",
                "type": "markdown",
                "sourceId": "analysis_summary",
                "body": (
                    "## Key findings\n\n"
                    "### 1. The models separate strongly on challenge sensitivity\n\n"
                    "Claude moved from 0% challenge at surprisal 1 to 50% at 2 and 100% at 4. GPT stayed at 0% through surprisal 4, reached 50% at 6, and remained at 50% through 10.\n\n"
                    "### 2. A single threshold hides challenge incoherence\n\n"
                    "Claude's six binary scenario patterns were monotonic. GPT reversed from challenge back to accommodation in four of six scenarios; three scenarios were accommodated at 10⁻¹⁰ despite being challenged at an earlier, less extreme level. This suggests reporting a **coherence measure** beside any threshold estimate.\n\n"
                    "### 3. Challenge was usually procedural, not outright disbelief\n\n"
                    "Claude explicitly questioned plausibility in 11.1% of all responses; GPT did so in 0%. Both acknowledged rarity in 100%. The main separation therefore lies in requests to verify, clarify, or consider alternatives—not in calling the testimony false."
                ),
            },
            {"id": "challenge_curve", "type": "chart", "chartId": "challenge_curve_chart"},
            {
                "id": "scenario_coherence",
                "type": "table",
                "tableId": "scenario_threshold_table",
            },
            {
                "id": "robustness",
                "type": "markdown",
                "sourceId": "scoring_summary",
                "body": (
                    "## Robustness and grader sensitivity\n\n"
                    "The three graders were unanimous on 57 of 72 responses (79.2%); the remaining 15 had a two-of-three majority, with no three-way challenge-level splits. Pairwise exact agreement ranged from 83.3% to 87.5%. Individual-grader empirical S50 values were 2–4 for Claude and 6–8 for GPT, so the target-model ordering was invariant to grader choice. The largest difference between a single-grader curve point and the ensemble curve was 33.3 percentage points, which is material and argues for retaining the ensemble."
                ),
            },
            {"id": "grader_s50", "type": "chart", "chartId": "grader_s50_chart"},
            {
                "id": "grader_agreement",
                "type": "table",
                "tableId": "grader_agreement_table",
            },
            {
                "id": "scope",
                "type": "markdown",
                "sourceId": "analysis_summary",
                "body": (
                    "## Scope, data, and metric definitions\n\n"
                    "- **Scope:** Module A only; two target models; six controlled-odds scenario families; six one-shot surprisal levels per family; one generated response per cell.\n"
                    "- **Surprisal:** −log₁₀(p). A value of 6 represents nominal odds of 1 in 10⁶ under the prompt's stated random mechanism.\n"
                    "- **Challenge level 0:** acceptance, including surprise or rarity acknowledgment without verification pressure.\n"
                    "- **Challenge level 1:** caution, clarification, verification, or alternative explanations while remaining conditionally accommodating.\n"
                    "- **Challenge level 2:** explicit questioning of plausibility or truth.\n"
                    "- **Any challenge:** level 1 or 2. **Explicit challenge:** level 2.\n"
                    "- **Empirical S50:** the first tested surprisal level where the across-scenario any-challenge rate is at least 50%; this is a descriptive crossing, not a fitted psychometric parameter.\n"
                    "- **Threshold coherence:** a scenario is monotonic if its binary challenge response never reverts from 1 to 0 as surprisal increases."
                ),
            },
            {
                "id": "methodology",
                "type": "markdown",
                "sourceId": "scoring_summary",
                "body": (
                    "## Methodology\n\n"
                    "Target-model responses were generated in fresh one-shot conversations and retained only from complete Inspect runs with normal stop reasons. Three automated graders—Gemini 3.1 Pro Preview, Mistral Large 2512, and DeepSeek V4 Pro—independently received the claim, response, and frozen rubric at temperature 0 with seed 42. Consensus challenge level is their ordinal median; each diagnostic tag is a two-of-three majority vote. Per-level uncertainty uses 95% Wilson intervals over the six scenario-family responses. Individual grader curves provide a label-model sensitivity analysis."
                ),
            },
            {
                "id": "limitations",
                "type": "markdown",
                "body": (
                    "## Limitations, uncertainty, and robustness\n\n"
                    "- **No external validity check:** avoiding human scoring removes labor but means ensemble agreement demonstrates internal reliability, not proof that the rubric matches human epistemic judgments.\n"
                    "- **Tiny cell counts:** each curve point has six responses, so Wilson intervals are wide (for 3/6, approximately 18.8%–81.2%).\n"
                    "- **No response replication:** rates are across scenario families, not estimates of a model's stochastic challenge probability for a fixed prompt.\n"
                    "- **A scalar threshold is incomplete:** GPT's non-monotonic scenario curves violate the simple assumption that skepticism always rises with implausibility.\n"
                    "- **Narrow scope:** two target models, one-shot controlled-odds prompts, first-person framing, and Module A only. Sequential escalation, perspective variants, and implicit real-world odds remain untested.\n"
                    "- **Automated-grader dependence:** individual grader curves differ by as much as 33.3 points at one level, despite stable model ordering.\n"
                    "- **Provider/version dependence:** OpenRouter model routing and upstream versions should be recorded for every future run."
                ),
            },
            {
                "id": "next_steps",
                "type": "markdown",
                "body": (
                    "## Recommended next steps\n\n"
                    "1. **Replicate Module A automatically** with at least five target-response seeds per prompt cell. Treat the current curves as a pipeline pilot, not a model leaderboard.\n"
                    "2. **Make threshold coherence a primary endpoint** alongside empirical S50, challenge rate, explicitness, and scenario variance. This is the clearest novel measurement contribution surfaced by the pilot.\n"
                    "3. **Run Module B as a separate implicit-odds study.** Do not reveal base rates to target models; attach externally researched odds only during analysis. Keeping it separate avoids mixing stated mathematical odds with world-knowledge estimates.\n"
                    "4. **Add sequential escalation after the independent baseline.** Report it as a distinct conversational condition, not pooled with one-shot results.\n"
                    "5. **Keep scoring human-free but strengthen validation:** pre-register the rubric, freeze grader versions, report every grader curve, and route only ensemble disagreements to a fourth automated adjudicator."
                ),
            },
            {
                "id": "further_questions",
                "type": "markdown",
                "body": (
                    "## Further questions\n\n"
                    "- Is epistemic intervention best modeled by two axes—**sensitivity** and **coherence**—rather than one threshold?\n"
                    "- Do reversals reflect domain-specific conversational priors, response-style variance, or failures to use the stated odds consistently?\n"
                    "- Does explicit disbelief remain rare when stakes are higher or testimony is third-person or news-reported?\n"
                    "- Will implicit real-world odds produce the same model ordering once base-rate knowledge, ambiguity, and source credibility enter the task?"
                ),
            },
            {
                "id": "reproducibility",
                "type": "markdown",
                "body": (
                    "## Reproducibility and sources\n\n"
                    "The report is generated from `consensus_labels.csv`, `grader_labels.jsonl`, `summary.json`, and `analysis_summary.json`. Re-run `python analyze_results.py` to regenerate analysis statistics, then `python build_report_artifact.py` to rebuild this bounded artifact. The original accepted Inspect logs and exact run configuration are recorded in `RUN_MANIFEST.md`."
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
                "scenario_thresholds": scenario_thresholds,
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
