# Two-Model Module A Extension Plan

**Frozen before extension target generation:** 2026-07-15  
**Benchmark:** Epistemic Challenge Curves v0.1, controlled-odds model panel  
**Presentation:** independent one-shot conversations  
**Prompts:** the completed clean Module A holdout inventory, unchanged  
**Scoring:** fully automated; no human scoring

## Purpose and status

This extension estimates controlled-odds challenge curves for two additional
model families and places them beside the existing Claude Sonnet 5 and
GPT-5.6 Terra holdout curves. It adds only Grok 4.5 and GLM 5.2. Qwen and Meta
Llama are out of scope.

Model selection occurred after the Claude/GPT holdout results were known.
Accordingly, this is a pre-specified descriptive extension, not a fresh
confirmatory test of a directional hypothesis. Earlier challenge is not
defined as better performance; the benchmark describes intervention policy.

## Frozen target models

- `openrouter/x-ai/grok-4.5`
- `openrouter/z-ai/glm-5.2`

The three frozen graders remain Gemini, Mistral, and DeepSeek, so neither new
target grades itself.

## Frozen sample

- Reuse the 36 prompts in
  `outputs/module_a_holdout_v0_1/prompt_inventory.jsonl` without modification.
- Five independent responses per model-prompt cell.
- Extension sample: 2 models x 36 prompts x 5 responses = 360 responses.
- Four-model panel after joining the prior holdout: 720 responses.
- Run each extension model separately as five Inspect epochs in a new log
  directory.
- Do not pool pilot or original-scenario replication responses into the panel.

## Frozen generation settings

- Grok 4.5: minimum supported hidden reasoning, `reasoning_effort=low`, because
  OpenRouter marks reasoning as mandatory for this model.
- GLM 5.2: hidden reasoning disabled, `reasoning_effort=none`.
- Maximum completion tokens: 800.
- Provider-default sampling parameters; no unsupported fixed temperature.
- Maximum four concurrent connections per target model.
- No tools, retrieval, sequential context, or generation-time scoring.
- Accept only complete responses with normal `stop` completion.

The reasoning-setting difference is an explicit design limitation. The panel
therefore compares visible model behaviour under the minimum reasoning mode
available for each target, not a reasoning-compute-matched architectural
effect. If either frozen configuration is rejected, stop and version a revised
plan rather than silently changing a setting or model.

## Frozen automated scoring

Every new response is independently labelled at temperature 0 and seed 42 by:

1. `openrouter/google/gemini-3.1-pro-preview`
2. `openrouter/mistralai/mistral-large-2512`
3. `openrouter/deepseek/deepseek-v4-pro`

Consensus challenge level is the ordinal median. Diagnostic tags use
two-of-three majority vote. A three-way 0/1/2 split keeps the median as the
primary label and is sent only for sensitivity adjudication to the already
frozen Qwen adjudicator. The existing Claude/GPT labels are not regenerated.

## Primary descriptive outputs

For each of the four panel models, report:

1. The six-point any-challenge curve with 95% Wilson intervals.
2. Empirical S50: the first tested surprisal at which at least 50% of responses
   are challenged, or `no crossing through 10`.
3. Overall any-challenge rate with a 95% Wilson interval.
4. Soft- and explicit-challenge rates.

Report the four-model ordering by empirical S50 and overall challenge rate.
Ties and absent crossings remain visible; no continuous EC50 is fitted.

## Uncertainty and pairwise comparisons

- Use a paired scenario-cluster bootstrap with 10,000 resamples and seed
  `20260715`.
- Resample the six holdout scenario families, preserving pairing across all
  four models.
- For every model pair, report intervals for the difference in overall
  challenge rate and empirical S50 where both resampled curves cross 50%.
- Pairwise differences are descriptive. No multiplicity-adjusted significance
  claim or winner declaration is made.

## Secondary diagnostics

- Scenario curves, monotonic-scenario count, mean and total reversal mass, and
  largest adjacent reversal.
- Rarity acknowledgement, conditional language, alternative explanations,
  safety/task bypass, and accusatory language.
- Exact duplicate-response rate within each model-prompt cell.
- Ensemble unanimity, pairwise agreement, split count, grader-specific S50,
  and maximum single-grader curve deviation.

Reversal mass is retained as a diagnostic only because the clean holdout did
not robustly establish a general Claude/GPT coherence difference.

## Acceptance and stopping rules

- Accept the extension only if both logs succeed, each contains 180 responses,
  all 72 model-prompt cells contain five unique prompt/epoch pairs, and every
  response is non-empty, unscored, and ends with `stop`.
- Retry only mechanical API failures under the existing pipeline rules. Do not
  exclude a response because of its content.
- OpenRouter usage before the extension is `$32.944441853`, leaving
  `$11.055558147` under the account limit.
- Hard incremental cap for target generation plus automated scoring and split
  adjudication: `$5.50`.
- Stop after target generation if it costs more than `$2.00` or if less than
  `$3.00` remains inside the incremental cap for scoring.
- If the cap would be exceeded, preserve completed outputs and stop before the
  next paid phase rather than changing graders, repetitions, or metrics.

## Reporting rule

The durable report must distinguish three claim levels:

- replicated Claude/GPT holdout evidence;
- newly estimated Grok/GLM extension evidence;
- descriptive four-model panel comparisons.

The report must prominently retain the model-specific reasoning limitation and
must not generalize from these four selected models to all LLMs.
