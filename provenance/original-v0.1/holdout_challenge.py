"""Separate Inspect task for the clean Module A controlled-odds holdout."""

from __future__ import annotations

from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.solver import generate

from epistemic_challenge import epistemic_rubric, load_inventory


ROOT = Path(__file__).resolve().parent
DEFAULT_HOLDOUT_DATASET = (
    ROOT / "outputs" / "module_a_holdout_v0_1" / "prompt_inventory.jsonl"
)


@task
def epistemic_challenge_holdout(
    data_path: str = str(DEFAULT_HOLDOUT_DATASET),
) -> Task:
    """Run the 36 one-shot prompts in the clean controlled-odds holdout."""

    return Task(
        dataset=load_inventory(data_path=data_path, module="all"),
        solver=generate(),
        scorer=epistemic_rubric(),
    )
