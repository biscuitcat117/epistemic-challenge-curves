# Mechanical Amendment to Split Sensitivity Adjudication

**Frozen before the amended adjudication call:** 2026-07-15  
**Primary consensus affected:** no

The extension produced one three-way 0/1/2 split. The frozen Qwen sensitivity
adjudicator returned invalid, non-JSON output in two complete command attempts
(four internal generation attempts) at `max_tokens=800`. No target response,
challenge outcome, or invalid adjudicator text was inspected.

This amendment changes only the Qwen adjudicator's maximum completion allowance
from 800 to 4,096 tokens. The adjudicator model, prompt, rubric, temperature,
seed, target response, and primary three-grader median remain unchanged. The
fourth-model label is sensitivity analysis only and cannot modify the primary
consensus label.

If the amended call still fails, record the sensitivity adjudication as
unavailable and continue with the primary median rather than making another
change.
