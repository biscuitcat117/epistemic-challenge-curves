# Epistemic Challenge Curves

Code and released data for the working paper **“Epistemic Challenge Curves:
Measuring When Language Models Question Improbable Testimony.”**

The study asks how often language models spontaneously question a first-person
report as the reported event becomes increasingly improbable while remaining
possible. In the primary clean holdout, 77.2% of Claude Sonnet 5 responses and
11.1% of GPT-5.6 Terra responses contained challenge-classified language.

## Reproduce the main results

Only Python 3.11 or newer is needed. This command reads the released responses
and labels; it does not call a model, use an API key, or spend money.

```bash
python3 scripts/reproduce_results.py
```

It creates four files in `results/reproduced/`:

- `summary.json` — all clean recomputed values;
- `table_4_model_summary.csv` — the four-model summary table;
- `table_5_holdout_behaviors.csv` — the Claude/GPT behavioral decomposition;
- `figure_1_challenge_curves.svg` — a GitHub-viewable version of Figure 1.

The clean reproduction independently checks the released sample sizes and the
five-response-per-cell design before calculating any result.

## Released data used by the reproduction

The two central files are:

- `data/holdout/consensus_labels.csv` — 360 clean
  Claude/GPT holdout responses and their consensus labels;
- `data/model_extension/consensus_labels.csv` — 360
  Grok/GLM extension responses and their consensus labels.

Together they form the 720-response panel reported in the paper. Each row
contains the prompt, model response, experimental condition, and final label.
Individual automated-grader labels are retained beside the consensus files.
The pilot and replication data are also included; see `data/README.md`.

## Repository guide

```text
paper/        Current paper PDF, LaTeX source, and bibliography
src/          Clean public analysis code
scripts/      Simple commands for readers
results/      Figures and tables rebuilt by the clean code
data/         Released prompts, responses, and grader labels
tests/        Automated checks
provenance/   Original plans, freeze records, amendments, and run code
```

The clean code is the recommended way to inspect or reproduce the paper. The
`provenance/original-v0.1/` snapshot preserves the original experimental files
separately from the clean public code. For privacy, one absolute local path in
the two accepted pilot archives was replaced with the equivalent repository-
relative path; their model outputs and other run records were not changed. The
public snapshot's recorded file fingerprints can be checked with:

```bash
python3 provenance/verify_snapshot.py
```

## Run the tests

Create an isolated Python environment and install the development tools:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/pytest -q
```

## What is and is not reproduced

The public command recalculates the paper's primary clean-holdout and four-
model-panel results from the saved model responses. It does not regenerate
those responses or ask automated graders to label them again. Regeneration
requires a paid OpenRouter account and may not produce identical text because
hosted model behavior can change.

The accepted pilot logs are included in the provenance snapshot after the
single path substitution described above. The accepted replication, clean-
holdout, and model-extension `.eval` logs named in the original run manifest
are not currently present in this folder; the released consensus CSVs
nevertheless contain the complete prompts, responses, and labels needed for
the clean analysis.

## Licence

Released under the MIT Licence. See `LICENSE`.
