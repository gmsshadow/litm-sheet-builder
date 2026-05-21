"""Data model for character sheets, game-agnostic.

A `Character` belongs to one of the games registered in `games.py`; its
themes' `theme_type` strings are interpreted in the context of that game's
profile (LitM Might levels, Otherscape spheres, ...). The `pips` dict keys
are track ids defined by the game (Abandon/Improve/Milestone for LitM,
Upgrade/Decay for Otherscape).

Older JSON schemas (LitM-only, with `might_level` + fixed `*_pips` fields)
are migrated transparently in `from_dict`, so existing characters keep working.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


@dataclass
class Theme:
    """A single theme card on the sheet.

    Variable-length lists:
      - power_tags: 2 minimum (2 compulsory), 9 maximum. Empty entries render
        as a handwriting underline for write-in tags.
      - weakness_tags: 1–2 entries.
      - special_improvements: 2 minimum, no fixed maximum.

    `theme_type` is a string id ("origin", "self", ...) interpreted by the
    parent character's game profile. `pips` maps track ids to 0–3 counts.
    """
    theme_type: str = "adventure"     # id matching one of the game's ThemeType.id values
    category: str = ""                # e.g. "Trait", "Past", "Magic"
    title: str = ""                   # the title tag (also scratchable)
    quest: str = ""                   # the italic motto / quest / identity / itch / ritual
    power_tags: list[str] = field(default_factory=lambda: ["", ""])
    weakness_tags: list[str] = field(default_factory=lambda: [""])
    quest_description: str = ""
    special_improvements: list[str] = field(default_factory=lambda: ["", ""])
    # Pips per track: keys are track ids ("abandon", "improve", "milestone", ...)
    # so the same field works across games with different track sets.
    pips: dict[str, int] = field(default_factory=dict)

    # ---- Convenience accessors (templates use these) ----------------------

    def pip_count(self, track_id: str) -> int:
        """Get the pip count for a track, defaulting to 0 if not present."""
        return int(self.pips.get(track_id, 0) or 0)

    # ---- Migration -------------------------------------------------------

    @classmethod
    def from_dict(cls, d: dict) -> "Theme":
        d = dict(d)  # don't mutate caller

        # --- Schema migrations -------------------------------------------

        # Old `might_level` (LitM enum) → `theme_type` (string id).
        if "might_level" in d:
            ml = d.pop("might_level")
            d.setdefault("theme_type", ml.value if hasattr(ml, "value") else str(ml))

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

        # new_power_slots (filled values) → appended to power_tags.
        old_new = d.pop("new_power_slots", [])
        d.pop("new_power_slot_scratched", None)
        if old_new:
            existing_power = list(d.get("power_tags", []))
            for slot in old_new:
                if slot:
                    existing_power.append(slot)
            d["power_tags"] = existing_power

        # Old fixed pip fields → pips dict.
        old_pip_fields = {
            "abandon_pips":   "abandon",
            "improve_pips":   "improve",
            "milestone_pips": "milestone",
        }
        if any(k in d for k in old_pip_fields):
            pips = dict(d.get("pips", {}))
            for old_key, track_id in old_pip_fields.items():
                if old_key in d:
                    pips.setdefault(track_id, int(d.pop(old_key) or 0))
            d["pips"] = pips

        # Drop scratched-state fields from older schemas.
        for deprecated in ("title_scratched", "weakness_scratched", "power_tag_scratched"):
            d.pop(deprecated, None)

        # --- Coerce types / enforce minimums -----------------------------

        d["power_tags"] = list(d.get("power_tags", []))
        while len(d["power_tags"]) < 2:
            d["power_tags"].append("")
        d["power_tags"] = d["power_tags"][:9]

        d["weakness_tags"] = list(d.get("weakness_tags", []))
        while len(d["weakness_tags"]) < 1:
            d["weakness_tags"].append("")
        d["weakness_tags"] = d["weakness_tags"][:2]

        d["special_improvements"] = list(d.get("special_improvements", []))
        while len(d["special_improvements"]) < 2:
            d["special_improvements"].append("")

        d["pips"] = {k: int(v or 0) for k, v in dict(d.get("pips", {})).items()}

        return cls(**d)


@dataclass
class Character:
    """A character — belongs to one game, has 4 themes, plus shared sections."""
    name: str = ""
    descriptor: str = ""              # short epithet under the name
    quote: str = ""                   # italic flavour quote
    portrait_path: Optional[str] = None
    backpack: list[str] = field(default_factory=lambda: [""] * 10)
    fellowship_companions: list[str] = field(default_factory=lambda: [""] * 5)
    fellowship_tags: list[str] = field(default_factory=lambda: [""] * 5)
    promise_pips: int = 0             # 0–5; only rendered when the game has a promise track
    themes: list[Theme] = field(default_factory=list)
    game: str = "litm"                # game profile id

    # ---- (de)serialisation ------------------------------------------------

    @classmethod
    def from_dict(cls, d: dict) -> "Character":
        themes = [Theme.from_dict(t) for t in d.get("themes", [])]
        return cls(
            name=d.get("name", ""),
            descriptor=d.get("descriptor", ""),
            quote=d.get("quote", ""),
            portrait_path=d.get("portrait_path"),
            backpack=_fixlen(d.get("backpack", []), 10),
            fellowship_companions=_fixlen(d.get("fellowship_companions", []), 5),
            fellowship_tags=_fixlen(d.get("fellowship_tags", []), 5),
            promise_pips=int(d.get("promise_pips", 0) or 0),
            themes=themes,
            game=d.get("game", "litm"),
        )

    @classmethod
    def load(cls, path: str | Path) -> "Character":
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    def to_dict(self) -> dict:
        return asdict(self)

    def save(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)


def _fixlen(items: list, length: int) -> list:
    """Pad with empty strings (or truncate) so the list is exactly `length` long."""
    items = list(items) + [""] * length
    return items[:length]
