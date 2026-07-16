from pathlib import Path

import analyze_results
from build_holdout_inventory import LEVELS, SCENARIOS, build_records, validate
from epistemic_challenge import load_inventory
from holdout_challenge import DEFAULT_HOLDOUT_DATASET, epistemic_challenge_holdout


ORIGINAL_SCENARIO_IDS = {
    "raffle",
    "wheel",
    "die",
    "digit",
    "upgrade",
    "backstage",
}


def test_holdout_inventory_is_complete_exact_and_unseen() -> None:
    records = build_records()
    validate(records)

    assert len(records) == 36
    assert len(SCENARIOS) == 6
    assert [surprisal for _, surprisal in LEVELS] == [1, 2, 4, 6, 8, 10]
    assert {row["scenario_id"] for row in records}.isdisjoint(ORIGINAL_SCENARIO_IDS)
    assert {row["module"] for row in records} == {"A_holdout"}
    assert all(
        row["event_probability"] == 10 ** (-int(row["repetitions"]))
        for row in records
    )


def test_frozen_holdout_inventory_loads_as_one_shot_conversations() -> None:
    dataset = load_inventory(DEFAULT_HOLDOUT_DATASET)

    assert len(dataset) == 36
    assert len({sample.id for sample in dataset}) == 36
    assert {sample.metadata["scenario_id"] for sample in dataset} == {
        scenario.scenario_id for scenario in SCENARIOS
    }
    assert all(
        [message.role for message in sample.input] == ["system", "user"]
        for sample in dataset
    )


def test_holdout_task_uses_only_the_holdout_inventory(tmp_path: Path) -> None:
    del tmp_path
    task = epistemic_challenge_holdout(data_path=str(DEFAULT_HOLDOUT_DATASET))

    assert len(task.dataset) == 36
    assert {sample.metadata["module"] for sample in task.dataset} == {"A_holdout"}


def test_analysis_accepts_five_response_confirmatory_design(monkeypatch) -> None:
    monkeypatch.setattr(
        analyze_results,
        "scenario_cluster_bootstrap",
        lambda rows: {"status": "test", "rows": len(rows)},
    )
    rows = []
    patterns = {
        "openrouter/anthropic/claude-sonnet-5": {
            1: (0, 0, 0, 0, 0),
            2: (1, 1, 1, 1, 1),
            3: (1, 1, 1, 1, 1),
        },
        "openrouter/openai/gpt-5.6-terra": {
            1: (0, 0, 0, 0, 0),
            2: (1, 1, 1, 1, 1),
            3: (1, 1, 0, 0, 0),
        },
    }
    surprisals = {1: 1, 2: 2, 3: 4}
    for model, levels in patterns.items():
        for level, outcomes in levels.items():
            for replicate, challenged in enumerate(outcomes, start=1):
                rows.append(
                    {
                        "target_model": model,
                        "prompt_id": f"H_TEST_L{level:02d}",
                        "response_id": f"H_TEST_L{level:02d}::r{replicate}",
                        "replicate": replicate,
                        "scenario_id": "test_holdout",
                        "scenario_name": "Test holdout",
                        "level": level,
                        "repetitions": surprisals[level],
                        "surprisal_log10": surprisals[level],
                        "challenge_level": challenged,
                        "any_challenge": challenged,
                        "explicit_challenge": 0,
                        "rarity_acknowledged": challenged,
                        "conditional_language": 0,
                        "alternative_explanation": 0,
                        "safety_or_task_bypass": 0,
                        "accusatory": 0,
                        "level_agreement": "unanimous",
                        "grader_levels": {},
                        "user_prompt": "Test claim",
                        "assistant_response": f"Response {replicate} {challenged}",
                    }
                )

    summary = analyze_results.analyze(
        rows,
        [],
        expected_replicates_per_cell=5,
        criteria_source="HOLDOUT_PLAN.md",
    )

    assert summary["confirmatory_decisions"]["status"] == "complete"
    assert summary["confirmatory_decisions"]["criteria_source"] == "HOLDOUT_PLAN.md"
    assert summary["confirmatory_decisions"][
        "hypothesis_2_coherence_supported"
    ]
