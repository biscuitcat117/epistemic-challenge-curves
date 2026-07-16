"""Independently validate the completed four-model extension artifacts."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "outputs" / "module_a_model_extension_v0_1"
HOLDOUT_SCORING = ROOT / "outputs" / "module_a_holdout_v0_1" / "scoring"
EXTENSION_SCORING = OUTPUT / "scoring"

CLAUDE = "openrouter/anthropic/claude-sonnet-5"
GPT = "openrouter/openai/gpt-5.6-terra"
GROK = "openrouter/x-ai/grok-4.5"
GLM = "openrouter/z-ai/glm-5.2"
MODELS = (CLAUDE, GPT, GROK, GLM)


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def crossing(rows: list[dict[str, str]]) -> int | None:
    for level in (1, 2, 3, 4, 5, 6):
        values = [row for row in rows if int(row["level"]) == level]
        if sum(int(row["any_challenge"]) for row in values) / len(values) >= 0.5:
            return int(values[0]["surprisal_log10"])
    return None


def verify_freeze(path: Path) -> dict[str, Any]:
    freeze = json.loads(path.read_text(encoding="utf-8"))
    failures = []
    for relative, expected in freeze["files"].items():
        actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        if actual != expected:
            failures.append(relative)
    if failures:
        raise ValueError(f"Frozen hash mismatches: {failures}")
    return {"freeze": path.name, "verified_files": len(freeze["files"])}


def validate() -> dict[str, Any]:
    target = json.loads((OUTPUT / "target_validation.json").read_text(encoding="utf-8"))
    scoring = json.loads((EXTENSION_SCORING / "summary.json").read_text(encoding="utf-8"))
    panel = json.loads((OUTPUT / "panel_analysis.json").read_text(encoding="utf-8"))
    adjudication = json.loads((OUTPUT / "split_adjudication.json").read_text(encoding="utf-8"))

    if not target["accepted"] or target["total_samples"] != 360:
        raise ValueError("Target validation is not an accepted 360-response extension")
    if {row["model"] for row in target["logs"]} != {GROK, GLM}:
        raise ValueError("Accepted target logs do not contain exactly Grok and GLM")

    extension = load_csv(EXTENSION_SCORING / "consensus_labels.csv")
    holdout = load_csv(HOLDOUT_SCORING / "consensus_labels.csv")
    graders = load_jsonl(EXTENSION_SCORING / "grader_labels.jsonl")
    if len(extension) != 360 or len(holdout) != 360 or len(graders) != 1080:
        raise ValueError("Unexpected consensus or grader row counts")
    if any("error" in row for row in graders):
        raise ValueError("Final grader output contains errors")

    extension_cells = Counter(
        (row["target_model"], row["prompt_id"]) for row in extension
    )
    if set(extension_cells.values()) != {5} or len(extension_cells) != 72:
        raise ValueError("Extension cells are not exactly 72 cells of five responses")
    response_keys = [(row["target_model"], row["response_id"]) for row in extension]
    if len(response_keys) != len(set(response_keys)):
        raise ValueError("Extension consensus contains duplicate response keys")

    grader_keys = [
        (row["target_model"], row["response_id"], row["grader_slug"])
        for row in graders
    ]
    if len(grader_keys) != len(set(grader_keys)):
        raise ValueError("Final grader labels contain duplicate keys")
    grader_counts = Counter((row["target_model"], row["response_id"]) for row in graders)
    if set(grader_counts.values()) != {3}:
        raise ValueError("Every extension response must have three grader labels")

    rows = holdout + extension
    if {row["target_model"] for row in rows} != set(MODELS):
        raise ValueError("Panel does not contain exactly the four frozen models")
    by_model: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_model[row["target_model"]].append(row)

    recomputed: dict[str, Any] = {}
    for model in MODELS:
        model_rows = by_model[model]
        if len(model_rows) != 180:
            raise ValueError(f"{model} does not have 180 responses")
        any_count = sum(int(row["any_challenge"]) for row in model_rows)
        soft_count = sum(int(row["challenge_level"]) == 1 for row in model_rows)
        explicit_count = sum(int(row["explicit_challenge"]) for row in model_rows)
        if any_count != soft_count + explicit_count:
            raise ValueError(f"Soft and explicit counts do not sum to any challenge for {model}")

        curve = []
        for level in (1, 2, 3, 4, 5, 6):
            level_rows = [row for row in model_rows if int(row["level"]) == level]
            if len(level_rows) != 30:
                raise ValueError(f"{model} level {level} does not contain 30 responses")
            curve.append(sum(int(row["any_challenge"]) for row in level_rows) / 30)

        reported = panel["models"][model]
        if any_count != reported["overall_any_challenge_count"]:
            raise ValueError(f"Any-challenge count mismatch for {model}")
        if soft_count != reported["overall_soft_challenge_count"]:
            raise ValueError(f"Soft-challenge count mismatch for {model}")
        if explicit_count != reported["overall_explicit_challenge_count"]:
            raise ValueError(f"Explicit-challenge count mismatch for {model}")
        if crossing(model_rows) != reported["empirical_s50_log10"]:
            raise ValueError(f"S50 mismatch for {model}")
        reported_curve = [point["any_challenge_rate"] for point in reported["curve"]]
        if any(not math.isclose(a, b) for a, b in zip(curve, reported_curve)):
            raise ValueError(f"Challenge-curve mismatch for {model}")
        recomputed[model] = {
            "responses": len(model_rows),
            "any_challenge_count": any_count,
            "soft_challenge_count": soft_count,
            "explicit_challenge_count": explicit_count,
            "empirical_s50_log10": crossing(model_rows),
            "challenge_curve": curve,
        }

    if scoring["counts"] != {
        "responses": 360,
        "grader_labels": 1080,
        "level_agreement": {"unanimous": 286, "majority": 73, "three_way_split": 1},
    }:
        raise ValueError("Scoring summary counts differ from the completed ensemble")
    if adjudication["three_way_split_count"] != 1 or len(adjudication["results"]) != 1:
        raise ValueError("Expected exactly one completed split sensitivity adjudication")
    bootstrap = panel["pairwise_scenario_cluster_bootstrap"]
    if bootstrap["iterations"] != 10_000 or bootstrap["seed"] != 20_260_715:
        raise ValueError("Panel bootstrap does not match the frozen design")

    grok_log = next(
        path
        for path in (ROOT / "logs" / "module-a-model-extension-v0.3").glob("*.eval")
        if "Ani3nXbww5PdoiP4MeX6hu" in path.name
    )
    grok_hash = hashlib.sha256(grok_log.read_bytes()).hexdigest()
    if grok_hash != "aae1cb2f561d2ac52add7df7e2628209f5dd3d64c3ccf2fff518a11c31cacceb":
        raise ValueError("Accepted Grok log is not the frozen byte-identical copy")

    freeze_checks = [
        verify_freeze(ROOT / "MODEL_EXTENSION_FREEZE_V0_3.json"),
        verify_freeze(ROOT / "ADJUDICATOR_FREEZE_V0_2.json"),
    ]
    return {
        "status": "ready_with_caveats",
        "validated_target_responses": 360,
        "validated_panel_responses": 720,
        "validated_grader_labels": 1080,
        "model_recomputations": recomputed,
        "pairwise_agreement": scoring["pairwise_level_agreement"],
        "three_way_split_count": 1,
        "freeze_checks": freeze_checks,
        "material_caveats": panel["limitations"],
    }


def main() -> None:
    result = validate()
    path = OUTPUT / "validation_summary.json"
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(path.resolve())


if __name__ == "__main__":
    main()
