# Authorized Mechanical Amendment to the Two-Model Extension

**Authorized by the user and frozen before any GLM v0.3 rerun:** 2026-07-15  
**Supersedes only the GLM completion ceiling in:**
`MODEL_EXTENSION_AMENDMENT_V0_2.md`  
**Response-content inspection before amendment:** none  
**Automated scoring before amendment:** none

## Trigger

The complete GLM v0.2 rerun produced 179 normally stopped, non-empty responses
and one empty response at the 1,600-token ceiling. The failed sample's metadata
reported 1,769 reasoning tokens. Only sample identity, epoch, stop reason,
response emptiness, and token-usage metadata were inspected. No response text,
challenge label, curve, or model comparison was inspected.

The user explicitly authorized the proposed v0.3 amendment after being told
that v0.2 did not pass the frozen acceptance rule.

## Frozen mechanical change

- Keep the accepted Grok 4.5 log byte-identical.
- Reject the entire GLM v0.2 log; do not replace only its failed cell.
- Rerun all 36 GLM prompts for five epochs in a new v0.3 log directory.
- Increase only GLM's maximum completion allowance from 1,600 to 4,096 tokens.
- Keep GLM `reasoning_effort=none`, maximum connections 4, provider-default
  sampling, no tools, and no generation-time scoring unchanged.
- Keep every prompt, grader, metric, bootstrap rule, sample size, and reporting
  rule in `MODEL_EXTENSION_PLAN.md` unchanged.

The v0.3 accepted-log directory must contain exactly the byte-identical Grok
log and the complete GLM v0.3 rerun. Both logs must pass the existing strict
180-response validator. If any v0.3 response still fails, stop before scoring.

## Budget status

OpenRouter usage before v0.3 is `$33.812443029`. Total extension spend to this
point is `$0.868001176`, leaving `$4.631998824` inside the original `$5.50`
incremental cap. The original target-phase and scoring-reserve rules remain in
force.
