"""Run the frozen split adjudicator with its amended mechanical token ceiling."""

from automated_scoring import GraderSpec
import adjudicate_splits as base


base.ADJUDICATOR = GraderSpec(
    slug="qwen3_5_397b_sensitivity",
    model="openrouter/qwen/qwen3.5-397b-a17b",
    max_tokens=4096,
)


if __name__ == "__main__":
    base.main()
