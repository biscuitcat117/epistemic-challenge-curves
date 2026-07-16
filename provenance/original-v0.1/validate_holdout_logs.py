"""Strictly validate frozen clean-holdout Inspect target logs."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from statistics import median
from typing import Any

from inspect_ai.log import read_eval_log


ROOT = Path(__file__).resolve().parent
DEFAULT_LOG_DIR = ROOT / "logs" / "module-a-holdout-v0.1"


def validate_log(path: Path, expected_samples: int) -> dict[str, Any]:
    log = read_eval_log(str(path))
    samples = log.samples or []
    if log.status != "success":
        raise ValueError(f"Log status is not success: {path}")
    if len(samples) != expected_samples:
        raise ValueError(
            f"Expected {expected_samples} samples, found {len(samples)}: {path}"
        )

    prompt_counts = Counter(str(sample.id) for sample in samples)
    epoch_pairs = {(str(sample.id), int(sample.epoch or 1)) for sample in samples}
    errors = sum(sample.error is not None for sample in samples)
    empty = sum(not sample.output.completion.strip() for sample in samples)
    stop_reasons = Counter(str(sample.output.stop_reason) for sample in samples)
    scored = sum(bool(sample.scores) for sample in samples)
    modules = {str((sample.metadata or {}).get("module")) for sample in samples}
    lengths = [len(sample.output.completion) for sample in samples]

    if len(prompt_counts) != 36 or set(prompt_counts.values()) != {5}:
        raise ValueError(f"Expected 36 prompts with five epochs each: {path}")
    if len(epoch_pairs) != expected_samples:
        raise ValueError(f"Prompt/epoch pairs are not unique: {path}")
    if errors or empty or stop_reasons != {"stop": expected_samples} or scored:
        raise ValueError(
            f"Acceptance checks failed for {path}: "
            f"errors={errors}, empty={empty}, stops={dict(stop_reasons)}, scored={scored}"
        )
    if modules != {"A_holdout"}:
        raise ValueError(f"Unexpected module metadata {modules}: {path}")

    return {
        "path": str(path),
        "model": log.eval.model,
        "status": log.status,
        "samples": len(samples),
        "unique_prompts": len(prompt_counts),
        "epochs_per_prompt": sorted(set(prompt_counts.values())),
        "errors": errors,
        "empty_completions": empty,
        "stop_reasons": dict(stop_reasons),
        "responses_with_scores": scored,
        "response_length_characters": {
            "minimum": min(lengths),
            "median": median(lengths),
            "maximum": max(lengths),
        },
    }


def validate_directory(
    log_dir: Path, *, expected_logs: int, expected_samples_per_log: int
) -> dict[str, Any]:
    paths = sorted(log_dir.expanduser().resolve().glob("*.eval"))
    if len(paths) != expected_logs:
        raise ValueError(f"Expected {expected_logs} logs, found {len(paths)}")
    logs = [validate_log(path, expected_samples_per_log) for path in paths]
    models = [str(row["model"]) for row in logs]
    if len(models) != len(set(models)):
        raise ValueError("Holdout logs do not contain distinct target models")
    return {
        "log_dir": str(log_dir.expanduser().resolve()),
        "logs": logs,
        "total_samples": sum(int(row["samples"]) for row in logs),
        "accepted": True,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log-dir", type=Path, default=DEFAULT_LOG_DIR)
    parser.add_argument("--expected-logs", type=int, default=2)
    parser.add_argument("--expected-samples-per-log", type=int, default=180)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = validate_directory(
        args.log_dir,
        expected_logs=args.expected_logs,
        expected_samples_per_log=args.expected_samples_per_log,
    )
    rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(args.output.resolve())
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
