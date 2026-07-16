# Mechanical Amendment to the Two-Model Extension

**Frozen before any GLM rerun:** 2026-07-15  
**Supersedes only the GLM completion ceiling in:** `MODEL_EXTENSION_PLAN.md`  
**Response-content inspection before amendment:** none  
**Automated scoring before amendment:** none

## Trigger

The frozen v0.1 target generation completed 180 samples for both models. The
strict acceptance validator accepted all 180 Grok responses but rejected the
GLM log because five responses ended at `max_tokens` with empty visible
completions. The five failures occurred at the 800-token ceiling. Only sample
IDs, epochs, stop reasons, response emptiness, and token-usage metadata were
inspected; no response text or challenge outcome was inspected.

## Frozen mechanical change

- Keep the complete accepted Grok 4.5 log unchanged.
- Reject the entire first GLM log; do not replace only the five failed cells.
- Rerun all 36 GLM prompts for five epochs in a new v0.2 log directory.
- Increase only GLM's maximum completion allowance from 800 to 1,600 tokens.
- Keep GLM `reasoning_effort=none`, maximum connections 4, provider-default
  sampling, no tools, and no generation-time scoring unchanged.
- Keep every prompt, grader, metric, bootstrap rule, sample size, and reporting
  rule in `MODEL_EXTENSION_PLAN.md` unchanged.

The larger ceiling prevents hidden reasoning from consuming the entire
allowance; it is not a content-based exclusion or prompt revision. The first
GLM log is retained as a rejected mechanical attempt and is never scored or
analysed.

## Accepted-log directory rule

The v0.2 accepted-log directory will contain exactly two logs:

1. a byte-identical copy of the already accepted Grok v0.1 log;
2. the complete GLM v0.2 rerun.

The acceptance validator must again require 180 normally stopped, non-empty,
unscored responses in each log. If any v0.2 GLM response still fails, stop and
do not make another unregistered change.

## Budget status

OpenRouter usage after the v0.1 target attempt is `$33.713719290`, so the
attempt cost `$0.769277437`. This remains below the frozen `$2.00` target-phase
cap. The rerun and all later scoring remain subject to the original `$5.50`
incremental hard cap measured from `$32.944441853`.
