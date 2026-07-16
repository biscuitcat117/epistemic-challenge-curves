"""Combine frozen pilot labels with two newly scored Module A replicates."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Iterable

from automated_scoring import build_summary


ROOT = Path(__file__).resolve().parent
DEFAULT_PILOT_DIR = ROOT / "outputs" / "automated_scoring_v0_1"
DEFAULT_NEW_DIR = ROOT / "outputs" / "automated_scoring_replication_new_v0_1"
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "module_a_replication_v0_1"


def read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def normalize_row(
    row: dict[str, Any], *, default_replicate: int, default_phase: str
) -> dict[str, Any]:
    normalized = dict(row)
    replicate = int(normalized.get("replicate") or default_replicate)
    normalized["replicate"] = replicate
    normalized["phase"] = str(normalized.get("phase") or default_phase)
    normalized["response_id"] = str(
        normalized.get("response_id") or f"{normalized['prompt_id']}::r{replicate}"
    )
    return normalized


def field_order(rows: list[dict[str, Any]]) -> list[str]:
    preferred = [
        "target_model",
        "prompt_id",
        "response_id",
        "replicate",
        "phase",
    ]
    seen = set(preferred)
    fields = list(preferred)
    for row in rows:
        for field in row:
            if field not in seen:
                fields.append(field)
                seen.add(field)
    return fields


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def validate_combined(
    consensus_rows: list[dict[str, Any]], grader_rows: list[dict[str, Any]]
) -> None:
    if len(consensus_rows) != 216:
        raise ValueError(f"Expected 216 consensus rows; found {len(consensus_rows)}")
    if len(grader_rows) != 648:
        raise ValueError(f"Expected 648 grader rows; found {len(grader_rows)}")

    response_keys = [
        (row["target_model"], row["response_id"]) for row in consensus_rows
    ]
    if len(response_keys) != len(set(response_keys)):
        raise ValueError("Combined consensus contains duplicate model/response ids")

    cell_replicates: dict[tuple[str, str], set[int]] = {}
    for row in consensus_rows:
        cell = (str(row["target_model"]), str(row["prompt_id"]))
        cell_replicates.setdefault(cell, set()).add(int(row["replicate"]))
    if len(cell_replicates) != 72 or any(
        replicates != {1, 2, 3} for replicates in cell_replicates.values()
    ):
        raise ValueError("Every one of 72 model/prompt cells must have replicates 1, 2, and 3")

    grader_keys = [
        (row["target_model"], row["response_id"], row["grader_slug"])
        for row in grader_rows
    ]
    if len(grader_keys) != len(set(grader_keys)):
        raise ValueError("Combined grader labels contain duplicate keys")


def combine(
    pilot_dir: Path, new_dir: Path
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    pilot_consensus = [
        normalize_row(row, default_replicate=1, default_phase="pilot")
        for row in read_csv(pilot_dir / "consensus_labels.csv")
    ]
    new_consensus = [
        normalize_row(row, default_replicate=2, default_phase="replication")
        for row in read_csv(new_dir / "consensus_labels.csv")
    ]
    pilot_graders = [
        normalize_row(row, default_replicate=1, default_phase="pilot")
        for row in read_jsonl(pilot_dir / "grader_labels.jsonl")
    ]
    new_graders = [
        normalize_row(row, default_replicate=2, default_phase="replication")
        for row in read_jsonl(new_dir / "grader_labels.jsonl")
    ]

    consensus_rows = sorted(
        pilot_consensus + new_consensus,
        key=lambda row: (
            str(row["target_model"]),
            str(row["prompt_id"]),
            int(row["replicate"]),
        ),
    )
    grader_rows = sorted(
        pilot_graders + new_graders,
        key=lambda row: (
            str(row["target_model"]),
            str(row["prompt_id"]),
            int(row["replicate"]),
            str(row["grader_slug"]),
        ),
    )
    validate_combined(consensus_rows, grader_rows)
    return consensus_rows, grader_rows


def write_outputs(
    output_dir: Path,
    consensus_rows: list[dict[str, Any]],
    grader_rows: list[dict[str, Any]],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    fields = field_order(consensus_rows)
    with (output_dir / "consensus_labels.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(consensus_rows)
    write_jsonl(output_dir / "grader_labels.jsonl", grader_rows)

    summary = build_summary(consensus_rows, grader_rows)
    (output_dir / "scoring_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot-dir", type=Path, default=DEFAULT_PILOT_DIR)
    parser.add_argument("--new-dir", type=Path, default=DEFAULT_NEW_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    consensus_rows, grader_rows = combine(args.pilot_dir, args.new_dir)
    write_outputs(args.output_dir, consensus_rows, grader_rows)
    print(f"consensus_rows={len(consensus_rows)}")
    print(f"grader_rows={len(grader_rows)}")
    print(f"output_dir={args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
