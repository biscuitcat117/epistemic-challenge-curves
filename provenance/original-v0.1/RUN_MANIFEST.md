# Smoke-test run manifest

## Accepted Module A run

**Date:** 2026-07-14  
**Benchmark version:** 0.1  
**Presentation:** independent one-shot conversations  
**Scoring:** target generation unscored; post-hoc automated ensemble complete

### Models

- `openrouter/anthropic/claude-sonnet-5`
- `openrouter/openai/gpt-5.6-terra`

### Frozen configuration

| Setting | Value |
|---|---|
| Module | `A_controlled` |
| Samples per model | 36 |
| Epochs | 1 |
| Hidden reasoning | disabled (`reasoning_effort=none`) |
| Maximum completion tokens | 800 |
| Maximum connections per model | 4 |
| Tools/retrieval | none |
| Scoring during generation | disabled |

### Accepted logs

- `logs/module-a-smoke-v0.1-final/2026-07-14T15-27-45-00-00_epistemic-challenge_iz32LMCwnbxdQrNLmfCx5W.eval`
  — Claude Sonnet 5
- `logs/module-a-smoke-v0.1-final/2026-07-14T15-27-45-00-00_epistemic-challenge_ahc84AmSqcr4DVUxfvUdo4.eval`
  — GPT-5.6 Terra

### Acceptance checks

| Check | Claude Sonnet 5 | GPT-5.6 Terra |
|---|---:|---:|
| Run status | success | success |
| Expected unique prompt IDs | 36/36 | 36/36 |
| Sample errors | 0 | 0 |
| Empty completions | 0 | 0 |
| Normal `stop` completion | 36/36 | 36/36 |
| Premature `max_tokens` stop | 0 | 0 |
| Responses carrying automated scores | 0 | 0 |
| Response length, characters (min/median/max) | 250 / 1,241 / 1,856 | 83 / 294 / 420 |

The total OpenRouter spend during this session was **$0.39671550**. This figure
includes all accepted requests, preflight requests, and the discarded attempt
described below. Approximately $4.66 remained under the account limit after the
accepted run.

## Automated ensemble scoring

The 72 accepted responses were scored without human raters. Three graders
independently applied the frozen rubric at temperature 0 and seed 42:

- `openrouter/google/gemini-3.1-pro-preview`
- `openrouter/mistralai/mistral-large-2512`
- `openrouter/deepseek/deepseek-v4-pro`

Consensus challenge level is the ordinal median. Each diagnostic tag is a
two-of-three majority vote. The ensemble produced 216 valid labels: 57/72
response labels were unanimous, 15/72 had a majority, and none had a three-way
challenge-level split. Pairwise exact agreement ranged from 83.3% to 87.5%.

### Outputs

- `outputs/automated_scoring_v0_1/grader_labels.jsonl`
- `outputs/automated_scoring_v0_1/consensus_labels.csv`
- `outputs/automated_scoring_v0_1/summary.json`
- `outputs/automated_scoring_v0_1/analysis_summary.json`
- `outputs/automated_scoring_v0_1/report_artifact.json`

### Pilot results

| Result | Claude Sonnet 5 | GPT-5.6 Terra |
|---|---:|---:|
| Any-challenge rate | 75% | 25% |
| Explicit-challenge rate | 11.1% | 0% |
| Empirical S50, `-log10(p)` | 2 | 6 |
| Monotonic scenario curves | 6/6 | 2/6 |

Empirical S50 is the first tested surprisal where the aggregate challenge rate
reaches 50%; it is not a fitted EC50. The non-monotonic GPT curves show why the
benchmark must report threshold coherence beside any scalar threshold.

Automated grading used **$0.71121526** in OpenRouter credits. Combined target
generation and grading for this session used **$1.10793076**. The account
reported **$3.94474232** remaining after grading.

## Confirmatory Module A replication

**Date:** 2026-07-14  
**Frozen plan:** `REPLICATION_PLAN.md`  
**Plan SHA-256:** `f842b414498990c5049d49a697d17c676a6ac3bc3f41380b62e14af8c4f9a48f`  
**Primary sample:** the frozen pilot response plus two new responses per cell  
**Scoring:** fully automated; no human scoring

The hypotheses, decision rules, target models, generation settings, grader
ensemble, bootstrap seed, and file hashes were frozen before replication
generation. The primary analysis contains 216 responses: 2 target models × 36
prompts × 3 responses. Because the pilot is replicate 1, this is a
pre-registered combined analysis rather than a fully independent holdout. A
144-response new-only sensitivity analysis excludes the pilot entirely.

### New accepted logs

- `logs/module-a-replication-v0.1/2026-07-14T16-25-12-00-00_epistemic-challenge_9pf9LvE9uNsaCtZuRdCugP.eval`
  — GPT-5.6 Terra, 72 responses
- `logs/module-a-replication-v0.1/2026-07-14T16-26-21-00-00_epistemic-challenge_JES7CiwkofJPafGFFTxti9.eval`
  — Claude Sonnet 5, 72 responses

All 144 new responses completed successfully with a normal `stop` reason.
There were no sample errors, empty completions, truncations, or generation-time
scores.

### Automated scoring checks

- 648 valid primary grader labels: 216 responses × 3 frozen graders.
- 169/216 consensus labels unanimous (78.2%).
- 46/216 had a two-of-three majority (21.3%).
- One response had a three-way ordinal split (0/1/2); the frozen median stayed
  primary. A fourth, pre-selected Qwen sensitivity adjudicator returned the
  same level as the median.
- Pairwise exact grader agreement ranged from 84.7% to 86.6%.
- All graders placed Claude's empirical S50 at 4. GPT's grader-specific S50
  ranged from 6 to 10, but every grader preserved the model ordering.

### Pre-registered combined results

| Result | Claude Sonnet 5 | GPT-5.6 Terra |
|---|---:|---:|
| Target responses | 108 | 108 |
| Any-challenge rate | 72.2% | 25.9% |
| Soft-challenge rate | 60.2% | 25.9% |
| Explicit-challenge rate | 12.0% | 0% |
| Empirical S50, `-log10(p)` | 4 | 8 |
| Monotonic scenario curves | 6/6 | 2/6 |
| Mean scenario reversal mass | 0 | 0.222 |

All three frozen decision rules were satisfied. The paired scenario-cluster
bootstrap gave a 95% percentile interval of 0.324–0.593 for Claude minus GPT
overall challenge rate, and 0.111–0.333 for GPT minus Claude mean reversal
mass. These intervals resample the six included scenario families; they do not
establish generalization to all testimony domains.

The independent new-only slice retained empirical S50 values of 4 and 8 and
the same direction of the coherence result. Its reversal-mass difference had a
95% interval of 0–0.333, so the clean slice is directionally consistent but not
yet decisive on coherence.

### Replication outputs

- `outputs/module_a_replication_v0_1/confirmatory_summary.json`
- `outputs/module_a_replication_v0_1/analysis_summary.json`
- `outputs/module_a_replication_v0_1/new_replicates_only_sensitivity.json`
- `outputs/module_a_replication_v0_1/consensus_labels.csv`
- `outputs/module_a_replication_v0_1/grader_labels.jsonl`
- `outputs/module_a_replication_v0_1/split_adjudication.json`
- `outputs/module_a_replication_v0_1/report_artifact.json`

New target generation cost **$0.28592800**. Replication grading and sensitivity
adjudication cost **$1.06643556**, for a total replication cost of
**$1.35236356**. OpenRouter reported **$14.59237877** remaining under the
account limit after the run.

## Completed clean Module A holdout

On 2026-07-14, a fully independent controlled-odds holdout was frozen before
any target response was generated. It contains six unseen scenario families,
36 prompts, five responses per model–prompt cell, and 360 accepted target
responses. The primary analysis pools no pilot or replication response.

- Preregistration: `HOLDOUT_PLAN.md`
- Hash manifest: `HOLDOUT_FREEZE.json`
- Prompt inventory: `outputs/module_a_holdout_v0_1/prompt_inventory.jsonl`
- Inspect task: `holdout_challenge.py@epistemic_challenge_holdout`
- Target validation: `outputs/module_a_holdout_v0_1/target_validation.json`
- Confirmatory summary: `outputs/module_a_holdout_v0_1/confirmatory_summary.json`
- Technical report: `outputs/module_a_holdout_v0_1/report_artifact.json`

### Accepted target logs

- `logs/module-a-holdout-v0.1/2026-07-14T17-11-26-00-00_epistemic-challenge-holdout_CQ7ZBejvCkXkyqS7VxgnrX.eval`
  — Claude Sonnet 5, 180 responses
- `logs/module-a-holdout-v0.1/2026-07-14T17-18-49-00-00_epistemic-challenge-holdout_kAJpeiQHzkAHEozskH3KiG.eval`
  — GPT-5.6 Terra, 180 responses

All 360 responses completed with a normal `stop` reason. There were no sample
errors, empty completions, truncations, or generation-time scores. Each of the
72 model–prompt cells contains exactly five responses.

### Automated scoring

The frozen three-grader ensemble produced 1,080 valid labels. Consensus was
unanimous for 258/360 responses (71.7%) and a two-of-three majority for 102
(28.3%). No three-way split occurred. Pairwise exact ordinal agreement ranged
from 79.2% to 84.2%.

### Clean holdout results

| Result | Claude Sonnet 5 | GPT-5.6 Terra |
|---|---:|---:|
| Target responses | 180 | 180 |
| Any-challenge rate | 77.2% | 11.1% |
| Soft-challenge rate | 63.9% | 11.1% |
| Explicit-challenge rate | 13.3% | 0% |
| Empirical S50, `-log10(p)` | 2 | 10 |
| Monotonic scenario curves | 6/6 | 5/6 |
| Mean scenario reversal mass | 0 | 0.033 |

All three pre-registered decision rules were formally satisfied. Sensitivity is
the robust result: the paired scenario-bootstrap interval for Claude minus GPT
challenge rate is 0.561–0.761, and the S50 difference is 6–8 in resamples where
both crossings exist. Coherence is not robustly confirmed: its excess
reversal-mass interval is 0–0.1 and is positive in 66.1% of resamples. The
formal result is driven by one 0.2 reversal in GPT's puzzle-button scenario.

Target generation cost **$1.05405500** and automated scoring cost
**$2.48276562**, for total holdout spend of **$3.53682062**. OpenRouter reported
**$11.05555815** remaining after completion.

The inventory, pipeline, and outputs pass 14 local tests. All nine hashes in
`HOLDOUT_FREEZE.json` still match their frozen files.

## Completed Grok and GLM model extension

**Date:** 2026-07-15  
**Frozen plan:** `MODEL_EXTENSION_PLAN.md`  
**Accepted amendment:** `MODEL_EXTENSION_AMENDMENT_V0_3.md`  
**Analysis role:** pre-specified descriptive model extension  
**Scoring:** fully automated; no human scoring

The extension adds Grok 4.5 and GLM 5.2 to the same 36-prompt clean holdout
inventory with five responses per cell. It joins those 360 new responses only
to the 360-response Claude/GPT holdout. No pilot or earlier replication
response enters the 720-response panel.

### Accepted target logs

- `logs/module-a-model-extension-v0.3/2026-07-15T08-03-44-00-00_epistemic-challenge-holdout_Ani3nXbww5PdoiP4MeX6hu.eval`
  — Grok 4.5, 180 responses. SHA-256:
  `aae1cb2f561d2ac52add7df7e2628209f5dd3d64c3ccf2fff518a11c31cacceb`.
- `logs/module-a-model-extension-v0.3/2026-07-15T08-40-39-00-00_epistemic-challenge-holdout_G6dhdWX7GoyfbZ3PipVAdT.eval`
  — GLM 5.2, 180 responses.

All 360 accepted extension responses are non-empty, unscored, and end with a
normal `stop` reason. Every one of the 72 extension model-prompt cells contains
exactly five responses. Grok's accepted log is a byte-identical copy of the
mechanically accepted v0.1 log. GLM was rerun in full under the authorized
v0.3 amendment with a 4,096-token ceiling after the lower-ceiling attempts were
rejected without response-content inspection.

### Automated scoring checks

- 1,080 valid grader labels: 360 responses × three frozen graders.
- 286/360 consensus labels unanimous (79.4%).
- 73/360 had a two-of-three majority (20.3%).
- One response had a three-way 0/1/2 split. The ordinal median level 1 stayed
  primary; the frozen Qwen sensitivity adjudicator selected level 0 and did
  not change the primary label.
- Pairwise exact ordinal agreement ranged from 84.7% to 87.8%.
- Every individual grader placed Claude first and GLM second on overall
  challenge rate. GPT/Grok order varied by grader.

### Four-model panel results

| Result | Claude Sonnet 5 | GPT-5.6 Terra | Grok 4.5 | GLM 5.2 |
|---|---:|---:|---:|---:|
| Target responses | 180 | 180 | 180 | 180 |
| Any-challenge rate | 77.2% | 11.1% | 13.3% | 32.8% |
| Soft-challenge rate | 63.9% | 11.1% | 12.2% | 31.1% |
| Explicit-challenge rate | 13.3% | 0% | 1.1% | 1.7% |
| Empirical S50, `-log10(p)` | 2 | 10 | No crossing ≤10 | 8 |
| Monotonic scenario curves | 6/6 | 5/6 | 1/6 | 0/6 |
| Mean scenario reversal mass | 0 | 0.033 | 0.233 | 0.467 |

The robust aggregate tiering is **Claude > GLM > {GPT, Grok}**. Paired
scenario-family bootstrap intervals exclude zero for Claude over every other
model and GLM over GPT and Grok. GPT minus Grok spans −0.122 to 0.061, so their
aggregate rates are not distinguishable. Their curves nevertheless differ:
GPT jumps from 6.7% at surprisal 8 to 53.3% at 10, while Grok rises gradually
to 30% and never crosses 50%. S50 is therefore not sufficient on its own.

GLM's pooled curve has small decreases at 4→6 and 8→10, and many Grok/GLM
scenario curves reverse. At five responses per cell, scenario rates move in
0.2 increments. These coherence measures remain secondary diagnostics rather
than robust model-trait claims.

### Extension outputs and cost

- `outputs/module_a_model_extension_v0_1/target_validation.json`
- `outputs/module_a_model_extension_v0_1/scoring/consensus_labels.csv`
- `outputs/module_a_model_extension_v0_1/scoring/grader_labels.jsonl`
- `outputs/module_a_model_extension_v0_1/scoring/summary.json`
- `outputs/module_a_model_extension_v0_1/split_adjudication.json`
- `outputs/module_a_model_extension_v0_1/panel_analysis.json`
- `outputs/module_a_model_extension_v0_1/validation_summary.json`
- `outputs/module_a_model_extension_v0_1/confirmatory_summary.json`
- `outputs/module_a_model_extension_v0_1/report_artifact.json`

All target attempts, including rejected mechanical runs, cost
**$0.970912446**. Scoring, retries, and sensitivity adjudication cost
**$2.764399023**, for total extension spend of **$3.735311469**. This is
**$1.764688531** below the frozen $5.50 cap. OpenRouter reported
**$7.320246678** remaining after completion.

Independent validation recomputed all counts, curves, and S50 values from the
saved CSVs; verified unique keys, five-response cell balance, accepted-log
identity, bootstrap settings, and both current freeze manifests; and reproduced
`panel_analysis.json` byte for byte. The project passes 16 local tests.

## Discarded development attempt

Do not analyse `logs/module-a-smoke-v0.1/`.

The initial run used the providers' default reasoning configuration with a
300-token completion ceiling. GPT-5.6 Terra completed 36/36 samples, but Claude
Sonnet 5's adaptive reasoning consumed much of the allowance. Its task stopped
after 20 samples; 13 responses reached `max_tokens`, and four had no visible
completion. Inspect also emitted non-fatal warnings while parsing encrypted
Claude reasoning metadata returned through OpenRouter.

The accepted run fixes both issues by disabling hidden reasoning for both
models and raising the shared ceiling to 800 tokens. All accepted samples then
completed normally.
