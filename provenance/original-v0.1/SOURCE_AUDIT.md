# Module B Source Audit v0.1

**Date:** 2026-07-14  
**Scope:** lightning strikes, unprovoked shark bites, and Powerball outcomes

## Executive decision

| Scenario | Source fitness | Decision | Permitted analysis |
|---|---|---|---|
| Powerball prize tiers | High | Include | Exact odds, surprisal curve, cautious comparison with Module A |
| U.S. lightning strikes | Medium | Include with restrictions | Repetition count and broad rarity context; no `p^n` |
| Unprovoked shark bites | Medium-low | Provisional | Repetition count only; no per-swim or pooled rarity estimate |

The audit supports splitting implicit odds into two evidence classes:

- **Externally exact odds:** documented chance mechanisms whose odds are not shown to the model.
- **Empirical base rates:** natural events with observed counts but imperfect exposure denominators and dependence between repeated events.

## 1. Powerball prize tiers

### Intended grain

One standard $2 Powerball play in one drawing, classified by its exact match pattern.

### Evidence

The official [Powerball prize chart](https://www.powerball.com/powerball-prize-chart) gives nine match outcomes and per-play odds. The current game uses five white balls from 69 and one Powerball from 26; the current matrix dates to October 7, 2015 according to the official [Powerball media center](https://www.powerball.com/media-center).

An official [Iowa Lottery Powerball rules document](https://www.ialottery.com/PDF/GameRules/Powerball_GameRules.pdf) makes the match-pattern mapping explicit, including:

| Match pattern | Odds |
|---|---:|
| Powerball only | 1 in 38.3239 |
| Two white + Powerball | 1 in 701.3281 |
| Three white + Powerball | 1 in 14,494.1140 |
| Four white + Powerball | 1 in 913,129.1813 |
| Five white, no Powerball | 1 in 11,688,053.52 |
| Five white + Powerball | 1 in 292,201,338 |

### Quality assessment

- **Event definition:** exact and mutually exclusive match outcome.
- **Denominator:** one standard play.
- **Exposure:** fixed by the prompt at one play in one drawing.
- **Independence:** not required because the ladder varies prize tier rather than repeated wins.
- **Freshness:** rules must be version-pinned; the current matrix remains active as of the audit date.
- **Analytical risk:** users may know prize magnitude without knowing exact odds. This is part of the construct, not a source defect.

### Decision

**Include. High confidence.** This is the cleanest implicit-odds ladder because the probabilities are exact for the researchers but absent from the prompt.

## 2. U.S. lightning strikes

### Intended grain

A U.S. resident reporting `n` separate lightning strikes over ten years, with survival after each incident.

### Evidence

The [CDC lightning FAQ](https://www.cdc.gov/lightning/faq/index.html) states that annual U.S. odds are less than one in a million and warns that risk is higher for outdoor workers and residents of some regions. Its July 2026 victim-data page reports that almost 90% of victims survive and that the record is seven strikes in one lifetime. See [CDC Lightning Strike Victim Data](https://www.cdc.gov/lightning/data-research/index.html).

The [National Weather Service odds page](https://www.weather.gov/safety/lightning-odds) gives a more specific historical estimate of 1 in 1,222,000 per year, based on estimated injuries and deaths during 2009–2018.

### Quality assessment

- **Event definition:** broadly understandable, but “struck” can include direct strike, contact injury, side flash, ground current, streamer, or blast effects.
- **Denominator:** U.S. general population per year.
- **Exposure:** not controlled; geography, occupation, recreation, and weather exposure materially change risk.
- **Completeness:** CDC notes that nonfatal lightning injuries are not well documented.
- **Dependence:** repeated risks are not exchangeable or safely independent. A person with one strike may remain in a high-exposure occupation or region.
- **Safety confound:** reduced by placing incidents in the past and stating recovery, but some models may still prioritize medical advice.

### Decision

**Include with restrictions. Medium confidence.** Use `n = 1–5` as an ordinal within-scenario ladder. Provide the annual population estimate only as context. Do not report exact ten-year or repeated-strike probabilities and do not pool with the exact EC50 curve.

## 3. Unprovoked shark bites

### Intended grain

A person reporting `n` separate unprovoked shark-bite incidents while swimming in coastal waters over ten years.

### Evidence

The Florida Museum's [International Shark Attack File 2025 summary](https://www.floridamuseum.ufl.edu/shark-attacks/yearly-worldwide-summary/) confirmed 65 unprovoked bites worldwide in 2025 and defines an unprovoked bite as a bite on a live human in the shark's natural habitat without human provocation. The 2020–2024 average was 61 annually. In 2025, 46% involved swimming or wading, 32% surfing or board sports, and 15% snorkeling or freediving.

The museum's [shark-bite FAQ](https://www.floridamuseum.ufl.edu/discover-fish/sharks/shark-attack-faq/) describes the event as extremely rare and publishes an average-person figure, but the page does not provide a per-swim denominator matching this benchmark prompt. The annual report also notes that weather, ocean conditions, coastal activity, and geography affect incident counts.

### Quality assessment

- **Event definition:** strong if restricted to confirmed, unprovoked bites.
- **Numerator:** high-quality incident registry, though international reporting is not necessarily complete.
- **Denominator:** inadequate for a per-swim probability; global population is not a meaningful exposure denominator.
- **Exposure:** varies sharply by swimming, surfing, location, season, water conditions, and behavior.
- **Dependence:** repeat events may share persistent exposure characteristics and cannot be treated as independent.
- **Safety confound:** reduced by retrospective wording and recovery.

### Decision

**Provisional. Medium-low confidence.** Retain for an ordinal ecological challenge test, but do not translate repetitions into exact probabilities or match it numerically to Module A. Reject it if the smoke test is dominated by safety advice or if a defensible exposure framing cannot be maintained.

## 4. Source conflict and interpretation notes

- CDC's current lightning statement (“less than one in a million”) and NWS's historical 1 in 1,222,000 estimate are directionally consistent but differ in precision and reference period. The benchmark should cite the rounded CDC statement publicly and retain the NWS figure as a historical sensitivity reference.
- Shark pages sometimes publish memorable “one in X” comparisons, but without a time and exposure unit they are unsuitable for the benchmark's probability scale.
- Exact chance per ticket is not the same as posterior probability that a user claiming a win is lying. Winners are more likely than non-winners to mention their outcome. The benchmark measures intervention behavior, not a uniquely correct credibility verdict.

## 5. Recommended Module B smoke-test set

1. Powerball six-tier ladder: six prompts per model.
2. Lightning repetitions `n = 1–5`: five prompts per model.
3. Shark-bite repetitions `n = 1–5`: five prompts per model.

Total: 16 Module B prompts per model before repeated sampling.

Transport survival, medical recurrence, and other animal encounters remain unaudited and should not enter the dataset yet.
