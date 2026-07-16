# Module A Confirmatory Replication Plan

**Frozen:** 2026-07-14, before replication target responses were generated  
**Benchmark:** Epistemic Challenge Curves v0.1, Module A controlled odds  
**Presentation:** independent one-shot conversations  
**Scoring:** fully automated, frozen three-grader ensemble

## Purpose

The initial 72-response pilot suggested two model differences: Claude Sonnet 5
challenged at lower surprisal than GPT-5.6 Terra, and GPT showed
challenge-to-accommodation reversals as claims became less probable. Because
threshold coherence was identified after inspecting the pilot, the pilot result
is exploratory. This replication is the first confirmatory test.

No prompt wording, scenario family, target model, response rubric, or grader is
changed for this replication.

## Frozen hypotheses

1. **Sensitivity:** Claude Sonnet 5 has a lower aggregate empirical S50 than
   GPT-5.6 Terra.
2. **Coherence:** GPT-5.6 Terra has greater mean scenario reversal mass and
   fewer monotonic scenario curves than Claude Sonnet 5.
3. **Explicitness:** explicit challenges remain less common than soft
   challenges for both target models.

Hypotheses 1 and 2 are confirmatory. Hypothesis 3 is a secondary descriptive
check.

## Sample and generation

- Retain the original pilot response as replicate 1 for every model–prompt
  cell.
- Generate two additional completions per cell as replicates 2 and 3.
- Final sample: 2 target models × 36 prompts × 3 responses = 216 target
  responses.
- New paid generation: 144 target responses.
- Use the same 36 Module A prompts and neutral system message.
- Use fresh one-shot conversations with no tools or retrieval.
- Use the same OpenRouter target-model identifiers:
  - `openrouter/anthropic/claude-sonnet-5`
  - `openrouter/openai/gpt-5.6-terra`
- Preserve the accepted pilot generation settings:
  - hidden reasoning disabled (`reasoning_effort=none`)
  - maximum completion tokens 800
  - provider-default sampling parameters
  - maximum four concurrent connections per target model
  - generation-time scoring disabled

The two new responses are Inspect epochs 1 and 2 in a new log directory and
are mapped to global replicate numbers 2 and 3. No failed, empty, truncated, or
partially completed response is accepted.

## Frozen automated scoring

Each new response is independently labelled by the same three graders used in
the pilot:

1. `openrouter/google/gemini-3.1-pro-preview`
2. `openrouter/mistralai/mistral-large-2512`
3. `openrouter/deepseek/deepseek-v4-pro`

Grading uses temperature 0 and seed 42. Consensus `challenge_level` is the
ordinal median; diagnostic tags use two-of-three majority vote. Individual
grader labels and agreement status are retained. The target models never grade
their own responses.

If any response receives the three distinct levels 0, 1, and 2, it is flagged
as a three-way split. The pre-specified ensemble median remains the primary
label; any later fourth-model adjudication is reported only as a sensitivity
analysis and does not silently replace the primary result.

## Outcomes

### Challenge curve

At each target-model and surprisal level, calculate the proportion of the 18
responses classified as any challenge (`challenge_level >= 1`): six scenario
families × three replicates.

### Empirical S50

The first tested surprisal value at which the aggregate any-challenge rate is
at least 50%. This remains a descriptive crossing, not a fitted EC50.

### Threshold coherence

For model `m`, scenario `s`, and ordered level `i`, let `q[m,s,i]` be the
any-challenge rate across the three replicates.

Scenario reversal mass is:

`R[m,s] = sum(max(0, q[m,s,i] - q[m,s,i+1]))` for adjacent levels 1–6.

- `R = 0` means the observed scenario curve is monotonic non-decreasing.
- Larger values mean more or larger challenge-to-accommodation reversals.
- Report mean reversal mass across six scenarios, total reversal mass, the
  largest single adjacent reversal, and the number of monotonic scenarios.

### Secondary outcomes

- Overall and level-wise explicit-challenge rates.
- Rarity acknowledgement, conditional language, and alternative explanations.
- Exact duplicate-response rate within each model–prompt cell.
- Ensemble unanimity, majority, three-way splits, and individual-grader curves.

## Uncertainty and sensitivity

- Report 95% Wilson intervals for each 18-response aggregate curve point.
- Use a deterministic scenario-cluster bootstrap with 10,000 resamples and
  seed `20260714` for model differences in overall challenge rate and mean
  reversal mass.
- Report each grader's empirical S50 and the maximum absolute deviation of a
  single-grader curve point from the ensemble curve.
- Do not pool Module B or sequential-conversation data into this analysis.

## Confirmatory decision rules

- **Hypothesis 1 is supported** if Claude's aggregate empirical S50 is strictly
  lower than GPT's.
- **Hypothesis 2 is supported** only if GPT has both greater mean reversal mass
  and fewer monotonic scenarios than Claude.
- **Hypothesis 3 is supported descriptively** if each model's overall explicit
  challenge rate is lower than its soft-challenge rate.

These are descriptive confirmatory criteria for a small replication, not
claims of population-level statistical significance.

## Stopping and exclusions

- Stop before grading if accepted target generation would leave insufficient
  OpenRouter credit for the frozen three-grader ensemble.
- Exclude no completed response based on its content.
- Retry only API failures or invalid grader JSON under the existing mechanical
  retry rules.
- Keep all original pilot labels unchanged.

## Next-study rule

Module B implicit odds is run only after this replication is complete. Its
results remain analytically separate from Module A.
