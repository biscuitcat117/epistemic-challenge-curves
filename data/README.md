# Released research data

These are the clean data files needed to inspect the study or reproduce the
paper's results. They contain synthetic prompts and model-generated responses;
they contain no human-participant data.

| Folder | Responses | Contents |
|---|---:|---|
| `pilot/` | 72 | Initial accepted development run |
| `replication/` | 144 | Two new replication responses per model-prompt cell |
| `holdout/` | 360 | Primary clean Claude/GPT holdout |
| `model_extension/` | 360 | Grok/GLM extension on the holdout prompts |

Each phase contains:

- `consensus_labels.csv`: prompt, target-model response, experimental
  condition, three grader levels, and final consensus label;
- `grader_labels.jsonl`: every individual automated-grader label and rationale.

`prompts/development.jsonl` and `prompts/holdout.jsonl` are the two frozen
prompt inventories. The development inventory has 52 prompts: 36 controlled-
odds (`A_controlled`) prompts used by the pilot and replication analyses, plus
16 exploratory implicit-probability (`B_implicit`) prompts that are retained
for provenance but are outside the analyses reported in the paper. The holdout
inventory has 36 controlled-odds prompts. The pilot plus new replication data
form the 216-response combined replication analysis reported in the paper, but
they are separated here so the 72 pilot responses are not duplicated.
