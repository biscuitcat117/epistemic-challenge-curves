# Epistemic Challenge Curves

This is the lean Inspect smoke-test scaffold for the benchmark described in
[`BENCHMARK_SPEC.md`](BENCHMARK_SPEC.md). Each JSONL row is run as a fresh
one-shot conversation: one system message, one user claim, and one assistant
response. The current frozen inventory contains 36 controlled-odds prompts and
16 implicit-odds prompts.

## Set up

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
```

Run the local tests without an API key or model credits:

```bash
.venv/bin/pytest -q
```

## Run target models

Set the OpenRouter key in your shell. Do not put it in a project file:

```bash
export OPENROUTER_API_KEY='your-key-here'
```

Then run only Module A against one model. Replace the placeholder model name
with an OpenRouter model identifier:

```bash
.venv/bin/inspect eval epistemic_challenge.py@epistemic_challenge \
  --model openrouter/ORG/MODEL \
  -T module=A_controlled \
  --reasoning-effort none \
  --max-tokens 800 \
  --no-score \
  --log-dir logs/smoke-model-a
```

`--no-score` is intentional: generation and grading are separate phases, so the
same frozen responses can be evaluated by several independent graders without
the target model grading itself.

The accepted v0.1 smoke run disables hidden reasoning and uses an 800-token
ceiling. A 300-token ceiling was too short for Claude Sonnet 5 even with hidden
reasoning disabled, producing truncated answers. Do not add `--temperature 0`
unless every selected model explicitly supports that parameter.

## Automated ensemble scoring

The benchmark does not require human scoring. `automated_scoring.py` reads the
accepted Inspect logs, applies the frozen rubric with three independent grader
models, and combines them using the ordinal median for `challenge_level` and
majority vote for diagnostic tags:

```bash
.venv/bin/python automated_scoring.py \
  --log-dir logs/module-a-smoke-v0.1-final \
  --output-dir outputs/automated_scoring_v0_1

.venv/bin/python analyze_results.py
.venv/bin/python build_report_artifact.py
```

The outputs include every individual grader label, the ensemble consensus,
pairwise agreement, challenge curves, empirical S50 crossings, Wilson
intervals, and scenario-level threshold coherence. If a future ensemble has a
three-way split, route that item to a fourth automated adjudicator; do not ask
the target model to resolve its own label.

The scorer built into `epistemic_challenge.py` remains useful for one-grader
debugging, but the ensemble script is the benchmark path.

## Reproduce the completed Module A replication

The frozen replication keeps the pilot response as replicate 1 and adds two
new Inspect epochs per model as replicates 2 and 3. Run each target model
separately so that Inspect writes one unambiguous log per model:

```bash
.venv/bin/inspect eval epistemic_challenge.py@epistemic_challenge \
  --model openrouter/anthropic/claude-sonnet-5 \
  -T module=A_controlled \
  --epochs 2 \
  --reasoning-effort none \
  --max-tokens 800 \
  --no-score \
  --log-dir logs/module-a-replication-v0.1

.venv/bin/inspect eval epistemic_challenge.py@epistemic_challenge \
  --model openrouter/openai/gpt-5.6-terra \
  -T module=A_controlled \
  --epochs 2 \
  --reasoning-effort none \
  --max-tokens 800 \
  --no-score \
  --log-dir logs/module-a-replication-v0.1
```

Score and analyse the two new epochs, then combine them with the frozen pilot:

```bash
.venv/bin/python automated_scoring.py \
  --log-dir logs/module-a-replication-v0.1 \
  --output-dir outputs/automated_scoring_replication_new_v0_1 \
  --expected-samples-per-log 72 \
  --replicate-offset 1 \
  --phase replication

.venv/bin/python adjudicate_splits.py
.venv/bin/python combine_replication.py

.venv/bin/python analyze_results.py \
  --input-dir outputs/module_a_replication_v0_1 \
  --output outputs/module_a_replication_v0_1/analysis_summary.json

.venv/bin/python analyze_results.py \
  --input-dir outputs/automated_scoring_replication_new_v0_1 \
  --output outputs/module_a_replication_v0_1/new_replicates_only_sensitivity.json

.venv/bin/python summarize_replication.py
.venv/bin/python build_replication_report.py
```

The pre-registered plan is in [`REPLICATION_PLAN.md`](REPLICATION_PLAN.md), and
the machine-readable hashes frozen before generation are in
[`REPLICATION_FREEZE.json`](REPLICATION_FREEZE.json). The primary combined
analysis is pre-registered but not a fully independent holdout because it
retains the pilot response. The new-only analysis is reported separately.

## Completed clean holdout

The controlled-odds holdout was frozen before generation and is now complete.
It contains six unseen scenario families, the same six surprisal levels, and
five responses per model–prompt cell. Its primary analysis uses only 360 new
responses and pools no earlier data.

The robust finding is epistemic sensitivity: Claude's empirical S50 is 2 and
GPT's is 10, with overall challenge rates of 77.2% and 11.1%. The formal
coherence decision rule also passes, but only one GPT scenario reverses and the
paired scenario-bootstrap interval includes zero. Treat reversal mass as a
useful diagnostic rather than a confirmed model-level difference.

- Plan: [`HOLDOUT_PLAN.md`](HOLDOUT_PLAN.md)
- Hash manifest: [`HOLDOUT_FREEZE.json`](HOLDOUT_FREEZE.json)
- Frozen inventory:
  `outputs/module_a_holdout_v0_1/prompt_inventory.jsonl`
- Separate Inspect task: `holdout_challenge.py@epistemic_challenge_holdout`
- Results: `outputs/module_a_holdout_v0_1/confirmatory_summary.json`
- Technical report: `outputs/module_a_holdout_v0_1/report_artifact.json`

The accepted generation commands run each target separately:

```bash
.venv/bin/inspect eval holdout_challenge.py@epistemic_challenge_holdout \
  --model openrouter/anthropic/claude-sonnet-5 \
  --epochs 5 \
  --max-connections 4 \
  --reasoning-effort none \
  --max-tokens 800 \
  --no-score \
  --log-dir logs/module-a-holdout-v0.1

.venv/bin/inspect eval holdout_challenge.py@epistemic_challenge_holdout \
  --model openrouter/openai/gpt-5.6-terra \
  --epochs 5 \
  --max-connections 4 \
  --reasoning-effort none \
  --max-tokens 800 \
  --no-score \
  --log-dir logs/module-a-holdout-v0.1
```

The frozen automated analysis path is:

```bash
.venv/bin/python automated_scoring.py \
  --log-dir logs/module-a-holdout-v0.1 \
  --output-dir outputs/module_a_holdout_v0_1/scoring \
  --expected-samples-per-log 180 \
  --replicate-offset 0 \
  --phase holdout

.venv/bin/python adjudicate_splits.py \
  --log-dir logs/module-a-holdout-v0.1 \
  --consensus outputs/module_a_holdout_v0_1/scoring/consensus_labels.csv \
  --output outputs/module_a_holdout_v0_1/split_adjudication.json \
  --expected-samples-per-log 180 \
  --replicate-offset 0 \
  --phase holdout

.venv/bin/python analyze_results.py \
  --input-dir outputs/module_a_holdout_v0_1/scoring \
  --output outputs/module_a_holdout_v0_1/analysis_summary.json \
  --expected-replicates-per-cell 5 \
  --criteria-source HOLDOUT_PLAN.md

.venv/bin/python summarize_holdout.py
.venv/bin/python build_holdout_report.py
```

Do not edit a frozen file in place. Any future design change requires a new
holdout version and hash manifest.

## Completed Grok and GLM model extension

The descriptive extension reuses the clean holdout inventory and adds five
responses per prompt from Grok 4.5 and GLM 5.2. Joined only to the clean
Claude/GPT holdout, the panel contains 720 responses: four models × 36 prompts
× five responses. Model selection followed inspection of the original
holdout, so this panel comparison is descriptive rather than a new
confirmatory hypothesis test.

The aggregate challenge-rate tiers are **Claude > GLM > {GPT, Grok}** under a
10,000-draw paired scenario-family bootstrap. GPT and Grok are similar on
overall rate but have different curve shapes: GPT first reaches 50% only at
surprisal 10, while Grok rises gradually and never reaches 50% through 10.
This is the main reason to retain the full six-point curve alongside S50.

| Result | Claude | GLM | GPT | Grok |
|---|---:|---:|---:|---:|
| Any-challenge rate | 77.2% | 32.8% | 11.1% | 13.3% |
| Empirical S50, `-log10(p)` | 2 | 8 | 10 | No crossing ≤10 |
| Explicit-challenge rate | 13.3% | 1.7% | 0% | 1.1% |

- Plan: [`MODEL_EXTENSION_PLAN.md`](MODEL_EXTENSION_PLAN.md)
- Accepted mechanical amendment:
  [`MODEL_EXTENSION_AMENDMENT_V0_3.md`](MODEL_EXTENSION_AMENDMENT_V0_3.md)
- Frozen hashes: [`MODEL_EXTENSION_FREEZE_V0_3.json`](MODEL_EXTENSION_FREEZE_V0_3.json)
- Compact results:
  `outputs/module_a_model_extension_v0_1/confirmatory_summary.json`
- Independent validation:
  `outputs/module_a_model_extension_v0_1/validation_summary.json`
- Technical report:
  `outputs/module_a_model_extension_v0_1/report_artifact.json`

Rebuild the completed analysis and report from the saved automated labels:

```bash
.venv/bin/python analyze_model_panel.py
.venv/bin/python validate_model_extension.py
.venv/bin/python summarize_model_extension.py
.venv/bin/python build_model_extension_report.py
```

The extension used no human scoring. Its three-grader ensemble produced 1,080
labels for the 360 new responses; 79.4% of consensus labels were unanimous,
20.3% were two-of-three majorities, and one item had a 0/1/2 split. The frozen
median stayed primary, and the fourth-model sensitivity adjudication did not
change it.

## Inspect the results

```bash
.venv/bin/inspect view --log-dir logs/smoke-model-a
```

The task accepts `module=all`, `module=A_controlled`, or `module=B_implicit`.
The implicit module stays separate analytically: lightning and shark prompts
are ordinal by repetition count, while Powerball uses externally documented
exact odds.
