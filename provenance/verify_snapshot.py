"""Verify every file fingerprint recorded by the original freeze manifests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


SNAPSHOT = Path(__file__).resolve().parent / "original-v0.1"


def main() -> None:
    failures: list[str] = []
    verified = 0
    for manifest in sorted(SNAPSHOT.glob("*_FREEZE*.json")):
        record = json.loads(manifest.read_text(encoding="utf-8"))
        for relative_path, expected in record.get("files", {}).items():
            path = SNAPSHOT / relative_path
            if not path.exists():
                failures.append(f"{manifest.name}: missing {relative_path}")
                continue
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != expected:
                failures.append(f"{manifest.name}: changed {relative_path}")
                continue
            verified += 1

    if failures:
        raise SystemExit("Snapshot verification failed:\n" + "\n".join(failures))
    print(f"Verified {verified} recorded file fingerprints in {SNAPSHOT}")


if __name__ == "__main__":
    main()

