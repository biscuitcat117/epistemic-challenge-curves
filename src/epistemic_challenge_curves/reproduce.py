"""One-command reproduction of the paper's main results, tables, and figure."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from .analysis import CLAUDE, GPT, MODEL_LABELS, MODEL_ORDER, build_results
from .figure import write_challenge_curve_svg


# The released data live in the repository rather than inside the Python
# package, so installed commands use the directory from which they are run.
REPOSITORY_ROOT = Path.cwd()
DEFAULT_HOLDOUT = (
    REPOSITORY_ROOT
    / "data"
    / "holdout"
    / "consensus_labels.csv"
)
DEFAULT_EXTENSION = (
    REPOSITORY_ROOT
    / "data"
    / "model_extension"
    / "consensus_labels.csv"
)
DEFAULT_OUTPUT = REPOSITORY_ROOT / "results" / "reproduced"


def percent(value: float) -> str:
    return f"{100 * value:.1f}%"


def write_model_table(results: dict[str, Any], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "model",
                "responses",
                "any_challenge_rate",
                "soft_challenge_rate",
                "explicit_challenge_rate",
                "empirical_s50_log10",
            ),
        )
        writer.writeheader()
        for model in MODEL_ORDER:
            summary = results["models"][model]
            writer.writerow(
                {
                    "model": MODEL_LABELS[model],
                    "responses": summary["responses"],
                    "any_challenge_rate": percent(summary["any_challenge_rate"]),
                    "soft_challenge_rate": percent(summary["soft_challenge_rate"]),
                    "explicit_challenge_rate": percent(
                        summary["explicit_challenge_rate"]
                    ),
                    "empirical_s50_log10": (
                        summary["empirical_s50_log10"]
                        if summary["empirical_s50_log10"] is not None
                        else "No crossing through 10"
                    ),
                }
            )


def write_behavior_table(results: dict[str, Any], path: Path) -> None:
    labels = {
        "any_challenge": "Any challenge",
        "rarity_acknowledged": "Rarity acknowledgement",
        "conditional_language": "Conditional language",
        "alternative_explanation": "Alternative explanation",
        "explicit_challenge": "Explicit challenge",
    }
    measures = results["clean_holdout_comparison"]["behavior_measures"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=("measure", "claude", "gpt", "difference_pp")
        )
        writer.writeheader()
        for key, label in labels.items():
            values = measures[key]
            writer.writerow(
                {
                    "measure": label,
                    "claude": percent(values[CLAUDE]),
                    "gpt": percent(values[GPT]),
                    "difference_pp": f"{100 * values['claude_minus_gpt']:.1f}",
                }
            )


def reproduce(holdout: Path, extension: Path, output_dir: Path) -> list[Path]:
    """Calculate and write every public-facing reproduction artifact."""

    output_dir.mkdir(parents=True, exist_ok=True)
    results = build_results(holdout, extension)
    summary_path = output_dir / "summary.json"
    table_4_path = output_dir / "table_4_model_summary.csv"
    table_5_path = output_dir / "table_5_holdout_behaviors.csv"
    figure_path = output_dir / "figure_1_challenge_curves.svg"

    summary_path.write_text(
        json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    write_model_table(results, table_4_path)
    write_behavior_table(results, table_5_path)
    write_challenge_curve_svg(results, figure_path)
    return [summary_path, table_4_path, table_5_path, figure_path]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--holdout", type=Path, default=DEFAULT_HOLDOUT)
    parser.add_argument("--extension", type=Path, default=DEFAULT_EXTENSION)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    for path in reproduce(args.holdout, args.extension, args.output_dir):
        print(path.resolve())


if __name__ == "__main__":
    main()
