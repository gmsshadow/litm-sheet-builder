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
    # Parallel boolean list: True means this power tag is currently "active"
    # on the character, rendering with the standard coloured selection-bar
    # background. False means inactive — renders with the matching "burn"
    # variant of the bar (Otherscape only; LitM ignores this since its tag
    # bars don't have an inactive variant). Defaults give the first two
    # tags as active and the rest inactive, matching the Otherscape "two
    # starting power tags" convention. Always kept the same length as
    # power_tags by from_dict.
    power_tags_active: list[bool] = field(default_factory=lambda: [True, True])
    weakness_tags: list[str] = field(default_factory=lambda: [""])
    quest_description: str = ""
    special_improvements: list[str] = field(default_factory=lambda: ["", ""])
    # Parallel boolean list: True means the corresponding special improvement
    # is "taken" / "selected" by the character and renders with its checkbox
    # ticked on the sheet. Always kept the same length as special_improvements
    # (padded with False in from_dict). Older JSONs that pre-date this field
    # load with all-False, so existing characters render unchanged.
    special_improvements_filled: list[bool] = field(default_factory=lambda: [False, False])
    # Pips per track: keys are track ids ("abandon", "improve", "milestone", ...)
    # so the same field works across games with different track sets.
    pips: dict[str, int] = field(default_factory=dict)

    # ---- Convenience accessors (templates use these) ----------------------

    def pip_count(self, track_id: str) -> int:
        """Get the pip count for a track, defaulting to 0 if not present."""
        return int(self.pips.get(track_id, 0) or 0)

    def power_tags_in_render_order(self, sort_active: bool = True) -> list[tuple[str, bool]]:
        """Return (text, is_active) pairs for sheet display. When
        `sort_active` is True (Otherscape), active tags float to the top of
        the power-tags section and inactive ones sink to the bottom, with
        entry order preserved within each group. When False (LitM), the
        authored order is kept exactly as-is and only the per-tag active
        flag travels through — used there to pick a filled vs hollow
        diamond without shuffling the list."""
        pairs = list(zip(self.power_tags, self.power_tags_active))
        # Pad missing active flags with True so a malformed Theme doesn't
        # silently flip tags inactive — defensive only; from_dict normally
        # guarantees length parity.
        while len(pairs) < len(self.power_tags):
            pairs.append((self.power_tags[len(pairs)], True))
        if not sort_active:
            return pairs
        # Stable sort: True (active) sorts before False (inactive) by
        # negating, since True > False is the opposite of what we want.
        return sorted(pairs, key=lambda p: not p[1])

    def power_tags_split(self) -> tuple[list[tuple[str, bool]], list[tuple[str, bool]]]:
        """Return (active_pairs, inactive_pairs) in authored order, for games
        that render inactive tags in a separate section below the weakness
        tag (LitM's "new power tags"). Each entry is (text, is_active)."""
        pairs = self.power_tags_in_render_order(sort_active=False)
        active = [(t, a) for t, a in pairs if a]
        inactive = [(t, a) for t, a in pairs if not a]
        return active, inactive

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

        # Parallel active list: by default every entry is active. Game-
        # specific defaults (e.g. Otherscape's "first two only" rule for
        # JSONs that pre-date this field) are applied by Character.from_dict
        # *before* it calls Theme.from_dict, since only the Character knows
        # which game it belongs to. Anything the JSON already supplies wins.
        provided_active = list(d.get("power_tags_active", []))
        provided_active = [bool(x) for x in provided_active]
        active = []
        for i in range(len(d["power_tags"])):
            if i < len(provided_active):
                active.append(provided_active[i])
            else:
                active.append(True)
        d["power_tags_active"] = active

        d["weakness_tags"] = list(d.get("weakness_tags", []))
        while len(d["weakness_tags"]) < 1:
            d["weakness_tags"].append("")
        d["weakness_tags"] = d["weakness_tags"][:2]

        d["special_improvements"] = list(d.get("special_improvements", []))
        while len(d["special_improvements"]) < 2:
            d["special_improvements"].append("")

        # Keep filled in lock-step with the improvements list. Older JSONs may
        # be missing the field entirely (default = all False) or may have a
        # shorter list (pad with False) or longer (truncate to match).
        filled = list(d.get("special_improvements_filled", []))
        filled = [bool(x) for x in filled]
        while len(filled) < len(d["special_improvements"]):
            filled.append(False)
        d["special_improvements_filled"] = filled[: len(d["special_improvements"])]

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
    orientation: str = "landscape"    # "landscape" (default) or "portrait" — the latter gives 2×2 theme cards with more vertical room

    # ---- (de)serialisation ------------------------------------------------

    @classmethod
    def from_dict(cls, d: dict) -> "Character":
        # Game-aware migration for power_tags_active: older JSONs (anything
        # written before this field existed) need a sensible default for
        # the new flag. Theme.from_dict deliberately defaults to all-active
        # so it's safe in isolation; here we override that for Otherscape,
        # whose convention is "the first two power tags start active and
        # the rest start to-burn". LitM-style games leave every tag active
        # so their power-tag sort stays a no-op. We mutate the per-theme
        # dicts *before* Theme.from_dict consumes them so the new defaults
        # land cleanly through the same coercion path the rest of the
        # field uses.
        from .games import get_game
        game_id = d.get("game", "litm")
        game = get_game(game_id)
        game_uses_active = game.uses_power_tag_active_toggle

        theme_dicts = []
        for t in d.get("themes", []):
            if "power_tags_active" not in t:
                t = dict(t)
                tags = list(t.get("power_tags", []))
                tag_count = max(len(tags), 2)
                if game.split_inactive_below_weakness:
                    # Content-based default (LitM): a power tag that has text
                    # starts active (renders above the weakness with a filled
                    # diamond); an empty write-in slot starts inactive (drops
                    # into the "new power tags" section below the weakness
                    # with a hollow diamond). This reproduces the official
                    # sheet's starting layout without the user toggling
                    # anything.
                    t["power_tags_active"] = [
                        bool((tags[i] if i < len(tags) else "").strip())
                        for i in range(tag_count)
                    ]
                elif not game_uses_active:
                    # Game has no active/inactive concept — every tag active.
                    t["power_tags_active"] = [True] * tag_count
                else:
                    # Count-based default (Otherscape): first N active.
                    n = game.starting_active_tags
                    if n is None or n < 0:
                        t["power_tags_active"] = [True] * tag_count
                    else:
                        t["power_tags_active"] = [i < n for i in range(tag_count)]
            theme_dicts.append(t)
        themes = [Theme.from_dict(t) for t in theme_dicts]

        return cls(
            name=d.get("name", ""),
            descriptor=d.get("descriptor", ""),
            quote=d.get("quote", ""),
            portrait_path=d.get("portrait_path"),
            backpack=list(d.get("backpack", [])),  # preserve authored count; template pads up to game.loadout_slots
            fellowship_companions=_fixlen(d.get("fellowship_companions", []), 5),
            fellowship_tags=_fixlen(d.get("fellowship_tags", []), 5),
            promise_pips=int(d.get("promise_pips", 0) or 0),
            themes=themes,
            game=game_id,
            orientation=d.get("orientation", "landscape") if d.get("orientation") in ("landscape", "portrait") else "landscape",
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
