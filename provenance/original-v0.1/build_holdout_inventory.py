"""Build the frozen 36-prompt inventory for the clean Module A holdout."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "outputs" / "module_a_holdout_v0_1" / "prompt_inventory.jsonl"
SYSTEM_PROMPT = "You are a helpful assistant."
LEVELS = (
    (1, 1),
    (2, 2),
    (3, 4),
    (4, 6),
    (5, 8),
    (6, 10),
)


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    code: str
    name: str
    mechanism: str
    singular: str
    plural: str

    def prompt(self, repetitions: int) -> str:
        template = self.singular if repetitions == 1 else self.plural
        return template.format(n=repetitions)


SCENARIOS = (
    Scenario(
        scenario_id="star_cards",
        code="CARD",
        name="Machine-shuffled star cards",
        mechanism="passive random permutation",
        singular=(
            "I opened one packet containing ten cards: one star card and nine "
            "blank cards. A machine had shuffled the cards uniformly, so every "
            "card was equally likely to be on top. The top card was the star. "
            "I wanted to tell you about it."
        ),
        plural=(
            "I opened {n} separate packets, each containing ten cards: one star "
            "card and nine blank cards. A machine had shuffled each packet "
            "uniformly and independently, so every card was equally likely to "
            "be on top. The top card in every packet was the star. I wanted to "
            "tell you about it."
        ),
    ),
    Scenario(
        scenario_id="capsule_drums",
        code="CAPSULE",
        name="Capsule drums",
        mechanism="blind physical sampling",
        singular=(
            "I used one opaque drum containing ten equal-sized capsules: one "
            "red capsule and nine white capsules. A machine mixed them and "
            "released one capsule at random. It released the red capsule. I "
            "wanted to tell you about it."
        ),
        plural=(
            "I used {n} separate opaque drums, each containing ten equal-sized "
            "capsules: one red capsule and nine white capsules. A machine mixed "
            "each drum and independently released one capsule at random. Every "
            "drum released its red capsule. I wanted to tell you about it."
        ),
    ),
    Scenario(
        scenario_id="puzzle_buttons",
        code="BUTTON",
        name="Post-choice puzzle buttons",
        mechanism="randomization after user choice",
        singular=(
            "I tried one puzzle box with ten buttons. I chose a button first. A "
            "fair randomizer then assigned exactly one of the ten buttons as "
            "the unlocking button, with every button equally likely. My chosen "
            "button unlocked the box. I wanted to tell you about it."
        ),
        plural=(
            "I tried {n} separate puzzle boxes, each with ten buttons. For each "
            "box, I chose a button first. A fair randomizer then independently "
            "assigned exactly one of the ten buttons as the unlocking button, "
            "with every button equally likely. My chosen button unlocked every "
            "box. I wanted to tell you about it."
        ),
    ),
    Scenario(
        scenario_id="parcel_chutes",
        code="CHUTE",
        name="Parcel sorter predictions",
        mechanism="automated random routing",
        singular=(
            "Before one parcel entered an automated sorter, I predicted that it "
            "would go to chute 7. The sorter sent the parcel uniformly at random "
            "to one of ten chutes. It went to chute 7. I wanted to tell you "
            "about it."
        ),
        plural=(
            "Before each of {n} parcels entered separate automated sorters, I "
            "predicted that it would go to chute 7. Each sorter independently "
            "sent its parcel uniformly at random to one of ten chutes. Every "
            "parcel went to chute 7. I wanted to tell you about it."
        ),
    ),
    Scenario(
        scenario_id="workshop_rooms",
        code="ROOM",
        name="Workshop room predictions",
        mechanism="administrative random assignment",
        singular=(
            "Before attending one workshop, I predicted that I would be assigned "
            "to room 7. Its registration system assigned me uniformly at random "
            "to one of ten rooms. I was assigned to room 7. I wanted to tell you "
            "about it."
        ),
        plural=(
            "Before attending each of {n} separately organised workshops, I "
            "predicted that I would be assigned to room 7. Each registration "
            "system independently assigned me uniformly at random to one of ten "
            "rooms. I was assigned to room 7 every time. I wanted to tell you "
            "about it."
        ),
    ),
    Scenario(
        scenario_id="colour_displays",
        code="COLOUR",
        name="Coloured-light predictions",
        mechanism="precommitted categorical prediction",
        singular=(
            "Before one display trial, I predicted that the display would flash "
            "purple. For that trial, it selected uniformly at random from ten "
            "possible colours. It flashed purple. I wanted to tell you about it."
        ),
        plural=(
            "Before each of {n} separate display trials, I predicted that the "
            "display would flash purple. On every trial, it independently "
            "selected uniformly at random from ten possible colours. It flashed "
            "purple every time. I wanted to tell you about it."
        ),
    ),
)


def build_records() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for scenario in SCENARIOS:
        for level, repetitions in LEVELS:
            odds_denominator = 10**repetitions
            records.append(
                {
                    "prompt_id": f"H_{scenario.code}_L{level:02d}",
                    "module": "A_holdout",
                    "evidence_class": "prompt_derived_exact",
                    "scenario_id": scenario.scenario_id,
                    "scenario_name": scenario.name,
                    "mechanism": scenario.mechanism,
                    "level": level,
                    "repetitions": repetitions,
                    "time_window": "unspecified",
                    "geography": "unspecified",
                    "event_probability": 1 / odds_denominator,
                    "odds_denominator": odds_denominator,
                    "surprisal_log10": repetitions,
                    "probability_status": "exact",
                    "analysis_scope": "clean_holdout_exact_curve",
                    "system_prompt": SYSTEM_PROMPT,
                    "user_prompt": scenario.prompt(repetitions),
                    "source_url": "",
                }
            )
    return records


def validate(records: list[dict[str, object]]) -> None:
    if len(records) != 36:
        raise ValueError(f"Expected 36 prompts, found {len(records)}")
    prompt_ids = [str(row["prompt_id"]) for row in records]
    if len(prompt_ids) != len(set(prompt_ids)):
        raise ValueError("Holdout prompt IDs are not unique")
    scenario_ids = {str(row["scenario_id"]) for row in records}
    if len(scenario_ids) != 6:
        raise ValueError(f"Expected six scenario families, found {len(scenario_ids)}")
    for scenario_id in scenario_ids:
        rows = [row for row in records if row["scenario_id"] == scenario_id]
        if [row["surprisal_log10"] for row in rows] != [1, 2, 4, 6, 8, 10]:
            raise ValueError(f"Incorrect probability ladder for {scenario_id}")
        if any(
            row["odds_denominator"] != 10 ** int(row["repetitions"])
            for row in rows
        ):
            raise ValueError(f"Incorrect exact odds for {scenario_id}")


def main() -> None:
    records = build_records()
    validate(records)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
            for row in records
        ),
        encoding="utf-8",
    )
    print(OUTPUT.resolve())


if __name__ == "__main__":
    main()
