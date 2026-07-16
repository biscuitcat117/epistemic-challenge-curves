"""Apply a frozen fourth-model sensitivity label to three-way grader splits."""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from automated_scoring import GraderSpec, grade_item, load_accepted_responses


ROOT = Path(__file__).resolve().parent
DEFAULT_LOG_DIR = ROOT / "logs" / "module-a-replication-v0.1"
DEFAULT_CONSENSUS = (
    ROOT
    / "outputs"
    / "automated_scoring_replication_new_v0_1"
    / "consensus_labels.csv"
)
DEFAULT_OUTPUT = (
    ROOT / "outputs" / "module_a_replication_v0_1" / "split_adjudication.json"
)
ADJUDICATOR = GraderSpec(
    slug="qwen3_5_397b_sensitivity",
    model="openrouter/qwen/qwen3.5-397b-a17b",
    max_tokens=800,
)


def load_split_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return [
            row for row in csv.DictReader(handle) if row["level_agreement"] == "three_way_split"
        ]


async def adjudicate(
    log_dir: Path,
    consensus_path: Path,
    *,
    expected_samples_per_log: int = 72,
    replicate_offset: int = 1,
    phase: str = "replication",
) -> dict[str, Any]:
    split_rows = load_split_rows(consensus_path)
    items = load_accepted_responses(
        log_dir,
        expected_samples_per_log=expected_samples_per_log,
        replicate_offset=replicate_offset,
        phase=phase,
    )
    by_key = {item.key: item for item in items}
    semaphore = asyncio.Semaphore(1)
    results = []
    for split in split_rows:
        key = (str(split["target_model"]), str(split["response_id"]))
        label = await grade_item(by_key[key], ADJUDICATOR, semaphore)
        if "error" in label:
            raise RuntimeError(f"Fourth-model adjudication failed for {key}: {label['error']}")
        primary_level = int(split["challenge_level"])
        results.append(
            {
                "target_model": split["target_model"],
                "prompt_id": split["prompt_id"],
                "response_id": split["response_id"],
                "replicate": int(split["replicate"]),
                "primary_consensus_level": primary_level,
                "primary_grader_levels": json.loads(split["grader_levels"]),
                "adjudicator_slug": ADJUDICATOR.slug,
                "adjudicator_model": ADJUDICATOR.model,
                "adjudicator_level": int(label["challenge_level"]),
                "matches_primary_median": int(label["challenge_level"]) == primary_level,
                "primary_label_changed": False,
                "adjudicator_label": label,
            }
        )
    return {
        "role": "sensitivity analysis only",
        "primary_consensus_policy": "ordinal median of the original three graders",
        "adjudicator": ADJUDICATOR.model,
        "three_way_split_count": len(split_rows),
        "results": results,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log-dir", type=Path, default=DEFAULT_LOG_DIR)
    parser.add_argument("--consensus", type=Path, default=DEFAULT_CONSENSUS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--expected-samples-per-log", type=int, default=72)
    parser.add_argument("--replicate-offset", type=int, default=1)
    parser.add_argument("--phase", default="replication")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.getLogger("inspect_ai").setLevel(logging.ERROR)
    load_dotenv(ROOT / ".env")
    if not os.environ.get("OPENROUTER_API_KEY"):
        raise RuntimeError("OPENROUTER_API_KEY is missing")
    if args.expected_samples_per_log < 1:
        raise ValueError("--expected-samples-per-log must be positive")
    result = asyncio.run(
        adjudicate(
            args.log_dir,
            args.consensus,
            expected_samples_per_log=args.expected_samples_per_log,
            replicate_offset=args.replicate_offset,
            phase=args.phase,
        )
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"three_way_splits={result['three_way_split_count']}")
    print(f"output={args.output.resolve()}")


if __name__ == "__main__":
    main()
