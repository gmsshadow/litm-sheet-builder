"""Data model for Legend in the Mist character sheets.

The three Might levels determine theme banner color and icon:
  - Origin    → green  / leaf
  - Adventure → red    / sword
  - Greatness → purple / crown
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Optional


class MightLevel(str, Enum):
    ORIGIN = "origin"
    ADVENTURE = "adventure"
    GREATNESS = "greatness"

    @property
    def label(self) -> str:
        return {"origin": "Origin", "adventure": "Adventure", "greatness": "Greatness"}[self.value]

    @property
    def icon(self) -> str:
        """Filename stem of the SVG in static/icons/ (e.g. 'origin' → origin.svg)."""
        return self.value


@dataclass
class Theme:
    """A single theme card on the sheet.

    Variable-length lists:
      - power_tags: 2 minimum (2 compulsory), 9 maximum. Empty entries are
        rendered as a handwriting underline so the player can write in tags
        gained through play.
      - weakness_tags: 1–2 entries. The second is optional.
      - special_improvements: 2 minimum, no fixed maximum.

    Pip counts are 0–3 (Abandon / Improve / Milestone). Scratched state is not
    modelled — the burn-scratch glyph on the sheet is purely a visual cue for
    the player to pen-mark when they actually scratch a tag at the table.
    """
    might_level: MightLevel = MightLevel.ADVENTURE
    category: str = ""                # e.g. "Uncanny Being", "Magic", "Past"
    title: str = ""                   # the title tag, also scratchable
    quest: str = ""                   # italic quest motto (formerly `motto`)
    power_tags: list[str] = field(default_factory=lambda: ["", ""])
    weakness_tags: list[str] = field(default_factory=lambda: [""])
    quest_description: str = ""
    special_improvements: list[str] = field(default_factory=lambda: ["", ""])
    abandon_pips: int = 0
    improve_pips: int = 0
    milestone_pips: int = 0

    @classmethod
    def from_dict(cls, d: dict) -> "Theme":
        d = dict(d)  # don't mutate caller

        # --- Schema migrations: silently accept older field names ---------

        # motto → quest
        if "motto" in d:
            d.setdefault("quest", d["motto"])
            del d["motto"]

        # weakness_tag (str) → weakness_tags (list)
        if "weakness_tag" in d:
            d.setdefault("weakness_tags", [d["weakness_tag"]])
            del d["weakness_tag"]

        # special_improvement (str) → special_improvements (list)
        if "special_improvement" in d:
            existing = d["special_improvement"]
            d.setdefault("special_improvements", [existing] if existing else [])
            del d["special_improvement"]

        # new_power_slots (filled values) → appended to power_tags;
        # empty entries are dropped. The old new-power section is gone.
        old_new = d.pop("new_power_slots", [])
        d.pop("new_power_slot_scratched", None)
        if old_new:
            existing_power = list(d.get("power_tags", []))
            for slot in old_new:
                if slot:
                    existing_power.append(slot)
            d["power_tags"] = existing_power

        # Drop scratched-state fields from older schemas
        for deprecated in (
            "title_scratched",
            "weakness_scratched",
            "power_tag_scratched",
        ):
            d.pop(deprecated, None)

        # --- Coerce types / enforce minimum lengths -----------------------

        if "might_level" in d and isinstance(d["might_level"], str):
            d["might_level"] = MightLevel(d["might_level"])

        d["power_tags"] = list(d.get("power_tags", []))
        while len(d["power_tags"]) < 2:
            d["power_tags"].append("")
        d["power_tags"] = d["power_tags"][:9]   # cap at 9

        d["weakness_tags"] = list(d.get("weakness_tags", []))
        while len(d["weakness_tags"]) < 1:
            d["weakness_tags"].append("")
        d["weakness_tags"] = d["weakness_tags"][:2]   # cap at 2

        d["special_improvements"] = list(d.get("special_improvements", []))
        while len(d["special_improvements"]) < 2:
            d["special_improvements"].append("")

        return cls(**d)


@dataclass
class Character:
    name: str = ""
    descriptor: str = ""              # short epithet under the name
    quote: str = ""                   # italic flavour quote
    portrait_path: Optional[str] = None  # path relative to static/ (e.g. "images/kinsi.png")
    backpack: list[str] = field(default_factory=lambda: [""] * 10)  # 10 slots, two columns of 5
    themes: list[Theme] = field(default_factory=list)

    # ---- (de)serialisation -------------------------------------------------

    @classmethod
    def from_dict(cls, d: dict) -> "Character":
        themes = [Theme.from_dict(t) for t in d.get("themes", [])]
        return cls(
            name=d.get("name", ""),
            descriptor=d.get("descriptor", ""),
            quote=d.get("quote", ""),
            portrait_path=d.get("portrait_path"),
            backpack=_fixlen(d.get("backpack", []), 10),
            themes=themes,
        )

    @classmethod
    def load(cls, path: str | Path) -> "Character":
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    def to_dict(self) -> dict:
        out = asdict(self)
        # Enums need to become strings for round-trip JSON.
        for t in out["themes"]:
            t["might_level"] = t["might_level"].value if isinstance(t["might_level"], MightLevel) else t["might_level"]
        return out

    def save(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)


def _fixlen(items: list, length: int) -> list:
    """Pad with empty strings (or truncate) so the list is exactly `length` long."""
    items = list(items) + [""] * length
    return items[:length]
