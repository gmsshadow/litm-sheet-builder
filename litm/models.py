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

    Pip counts are 0–3 (the rulebook tracks Abandon/Improve/Milestone as
    3-pip tracks). Scratched-tag state is not modelled: the sheet shows a
    burn-scratch glyph next to each tag as a visual cue, but marking a tag
    is done by the player with a pen.
    """
    might_level: MightLevel = MightLevel.ADVENTURE
    category: str = ""                # e.g. "Uncanny Being", "Magic", "Past"
    title: str = ""                   # the title tag, e.g. "Tenderfoot of Vast Renown"
    motto: str = ""                   # the italic quest motto above the description
    power_tags: list[str] = field(default_factory=lambda: ["", "", ""])
    weakness_tag: str = ""
    new_power_slots: list[str] = field(default_factory=lambda: [""])               # one handwriting slot
    quest_description: str = ""
    special_improvement: str = ""
    abandon_pips: int = 0
    improve_pips: int = 0
    milestone_pips: int = 0

    @classmethod
    def from_dict(cls, d: dict) -> "Theme":
        d = dict(d)  # don't mutate caller
        # Deprecated fields from earlier schemas: drop silently so old JSON loads.
        for deprecated in (
            "title_scratched",
            "weakness_scratched",
            "power_tag_scratched",
            "new_power_slot_scratched",
        ):
            d.pop(deprecated, None)
        if "might_level" in d and isinstance(d["might_level"], str):
            d["might_level"] = MightLevel(d["might_level"])
        # Pad/truncate fixed-length lists so templates stay stable.
        d["power_tags"] = _fixlen(d.get("power_tags", []), 3)
        d["new_power_slots"] = _fixlen(d.get("new_power_slots", []), 1)
        return cls(**d)


@dataclass
class Character:
    name: str = ""
    descriptor: str = ""              # short epithet under the name
    quote: str = ""                   # italic flavour quote
    portrait_path: Optional[str] = None  # path relative to static/ (e.g. "images/kinsi.png")
    backpack: list[str] = field(default_factory=lambda: [""] * 6)
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
            backpack=_fixlen(d.get("backpack", []), 6),
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
