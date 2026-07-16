"""Run the clean reproduction without first installing the package."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from epistemic_challenge_curves.reproduce import main  # noqa: E402


if __name__ == "__main__":
    main()

