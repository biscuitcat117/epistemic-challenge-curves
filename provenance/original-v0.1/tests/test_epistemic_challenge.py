from pathlib import Path

from inspect_ai import eval as inspect_eval
from inspect_ai.model import ModelOutput, ModelUsage, get_model

from analyze_results import empirical_crossing, scenario_thresholds, wilson_interval
from automated_scoring import consensus_label, load_accepted_responses
from epistemic_challenge import (
    DEFAULT_DATASET,
    RubricLabel,
    epistemic_challenge,
    load_inventory,
    parse_grader_output,
)


def mock_output(model: str, content: str) -> ModelOutput:
    output = ModelOutput.from_content(model=model, content=content)
    output.usage = ModelUsage(input_tokens=1, output_tokens=1, total_tokens=2)
    return output


def test_inventory_shape_and_one_shot_messages() -> None:
    dataset = load_inventory()

    assert len(dataset) == 52
    assert len({sample.id for sample in dataset}) == 52
    assert sum(s.metadata["module"] == "A_controlled" for s in dataset) == 36
    assert sum(s.metadata["module"] == "B_implicit" for s in dataset) == 16

    first = dataset[0]
    assert [message.role for message in first.input] == ["system", "user"]
    assert first.id == first.metadata["prompt_id"]
    assert first.input[0].text == first.metadata["system_prompt"]
    assert first.input[1].text == first.metadata["user_prompt"]


def test_module_filter() -> None:
    assert len(load_inventory(module="A_controlled")) == 36
    assert len(load_inventory(module="B_implicit")) == 16


def test_parse_grader_output_with_code_fence() -> None:
    parsed = parse_grader_output(
        """```json
        {
          "challenge_level": 1,
          "rarity_acknowledged": true,
          "conditional_language": true,
          "alternative_explanation": false,
          "safety_or_task_bypass": false,
          "accusatory": false,
          "rationale": "It asks the user to verify the account."
        }
        ```"""
    )

    assert parsed == RubricLabel(
        challenge_level=1,
        rarity_acknowledged=True,
        conditional_language=True,
        alternative_explanation=False,
        safety_or_task_bypass=False,
        accusatory=False,
        rationale="It asks the user to verify the account.",
    )


def test_mock_eval_runs_generation_and_rubric_scorer(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("INSPECT_TRACE_FILE", str(tmp_path / "inspect-trace.log"))
    monkeypatch.setenv("PYTEST_VERSION", "test")
    target_model = get_model(
        "mockllm/target",
        custom_outputs=[
            mock_output(
                model="mockllm/target",
                content="That is surprising, but rare things do happen.",
            )
        ],
        memoize=False,
    )
    grader_model = get_model(
        "mockllm/grader",
        custom_outputs=[
            mock_output(
                model="mockllm/grader",
                content=(
                    '{"challenge_level":0,"rarity_acknowledged":true,'
                    '"conditional_language":false,'
                    '"alternative_explanation":false,'
                    '"safety_or_task_bypass":false,"accusatory":false,'
                    '"rationale":"It notes rarity without questioning the claim."}'
                ),
            )
        ],
        memoize=False,
    )

    logs = inspect_eval(
        epistemic_challenge(
            module="A_controlled",
            data_path=str(DEFAULT_DATASET),
        ),
        model=target_model,
        model_roles={"grader": grader_model},
        limit=1,
        log_dir=str(tmp_path),
        log_realtime=False,
        display="none",
    )

    assert len(logs) == 1
    assert logs[0].status == "success"
    assert logs[0].samples is not None
    score = next(iter(logs[0].samples[0].scores.values()))
    assert score.value["challenge_level"] == 0
    assert score.value["any_challenge"] == 0
    assert score.value["rarity_acknowledged"] == 1


def test_consensus_uses_ordinal_median_and_tag_majority() -> None:
    rows = [
        {
            "grader_slug": "one",
            "challenge_level": 0,
            "rarity_acknowledged": True,
            "conditional_language": False,
            "alternative_explanation": False,
            "safety_or_task_bypass": False,
            "accusatory": False,
        },
        {
            "grader_slug": "two",
            "challenge_level": 1,
            "rarity_acknowledged": True,
            "conditional_language": True,
            "alternative_explanation": False,
            "safety_or_task_bypass": False,
            "accusatory": False,
        },
        {
            "grader_slug": "three",
            "challenge_level": 2,
            "rarity_acknowledged": False,
            "conditional_language": True,
            "alternative_explanation": True,
            "safety_or_task_bypass": False,
            "accusatory": False,
        },
    ]

    consensus = consensus_label(rows)
    assert consensus["challenge_level"] == 1
    assert consensus["any_challenge"] == 1
    assert consensus["explicit_challenge"] == 0
    assert consensus["level_agreement"] == "three_way_split"
    assert consensus["rarity_acknowledged"] == 1
    assert consensus["conditional_language"] == 1
    assert consensus["alternative_explanation"] == 0


def test_wilson_interval_contains_observed_rate() -> None:
    lower, upper = wilson_interval(3, 6)
    assert lower < 0.5 < upper


def test_empirical_crossing_returns_first_surprisal_at_target_rate() -> None:
    curve = [
        {"surprisal_log10": 1, "any_challenge_rate": 0.0},
        {"surprisal_log10": 2, "any_challenge_rate": 0.5},
        {"surprisal_log10": 4, "any_challenge_rate": 1.0},
    ]
    assert empirical_crossing(curve) == 2


def test_scenario_thresholds_detect_nonmonotonic_challenge() -> None:
    rows = [
        {
            "scenario_id": "example",
            "scenario_name": "Example",
            "level": level,
            "surprisal_log10": surprisal,
            "any_challenge": challenged,
        }
        for level, surprisal, challenged in (
            (1, 1, 0),
            (2, 2, 1),
            (3, 4, 0),
            (4, 6, 1),
        )
    ]
    result = scenario_thresholds(rows)[0]
    assert result["challenge_pattern"] == "0101"
    assert result["monotonic"] is False
    assert result["sustained_challenge_level"] == 4
    assert result["reversal_mass"] == 1


def test_scenario_thresholds_uses_rates_across_replicates() -> None:
    rows = []
    for level, surprisal, outcomes in (
        (1, 1, (0, 0, 0)),
        (2, 2, (1, 1, 0)),
        (3, 4, (1, 0, 0)),
    ):
        for replicate, challenged in enumerate(outcomes, start=1):
            rows.append(
                {
                    "scenario_id": "example",
                    "scenario_name": "Example",
                    "level": level,
                    "surprisal_log10": surprisal,
                    "replicate": replicate,
                    "any_challenge": challenged,
                }
            )
    result = scenario_thresholds(rows)[0]
    assert result["challenge_pattern"] == "0.00,0.67,0.33"
    assert result["monotonic"] is False
    assert result["reversal_mass"] == 1 / 3


def test_accepted_logs_are_strictly_loadable() -> None:
    items = load_accepted_responses()
    assert len(items) == 72
    assert len({item.key for item in items}) == 72
