"""Game profile system.

Each supported tabletop game (Legend in the Mist, Otherscape, ...) is described
by a `GameProfile` that catalogs everything the engine needs to render that
game's character sheet: the theme type categories, the track types and ids,
the labels for re-skinned sections (Backpack vs Loadout, Fellowship vs Crew),
and the per-game asset paths.

The sheet template and editor template are generic and consult the profile
for anything game-specific. To add a new game, define a new `GameProfile`
below and register it in `GAMES`.
"""
from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ThemeType:
    """One of a game's theme categories (LitM Might levels, Otherscape spheres)."""
    id: str                  # internal identifier, matches the value stored in JSON ("origin", "self", ...)
    label: str               # display label ("Origin", "Self")
    color: str               # hex color used for the theme's accent
    icon: str                # filename in static/icons/ (e.g. "origin.svg")
    banner: str              # filename in static/images/ (e.g. "header-origin.webp")
    tag_bar: str = ""        # selection-bar image for power tags / title (Otherscape)
    quest_label: str = "Quest"   # what this theme's motto field is called (LitM: always "Quest", Otherscape: per-theme)


@dataclass(frozen=True)
class Track:
    """A 0–3 pip track on each theme (Abandon, Improve, etc.)."""
    id: str          # internal identifier ("abandon", "improve", "milestone", "decay", "upgrade")
    label: str       # display label ("Abandon", "Decay")


@dataclass(frozen=True)
class GameProfile:
    """Everything that varies between games."""
    id: str                          # "litm", "otherscape"
    name: str                        # "Legend in the Mist", "Otherscape"
    theme_types: list[ThemeType]     # ordered list of allowed theme types
    tracks: list[Track]              # the pip tracks each theme card carries

    # Re-skinnable section labels
    backpack_label: str              # "Backpack" / "Loadout"
    backpack_icon: str               # icon filename for the backpack banner

    fellowship_label: str            # "Fellowship Relationship" / "Crew Relationships"
    fellowship_companion_label: str  # "Companion" / "Crew Member"
    fellowship_tag_label: str        # "Relationship Tag"
    fellowship_icon: str = ""        # icon filename for the fellowship banner ("" = no icon)
    burn_icon: str = "burn-scratch-empty.svg"  # scratch marker on tags / theme title
    weakness_bar: str = ""           # selection-bar image for weakness tags (Otherscape)
    has_promise: bool = True         # whether the Promise pip track is shown
    promise_label: str = "Promise"
    promise_size: int = 5            # number of promise pips

    # Asset paths
    background: str = ""             # background image filename
    stylesheet: str = ""             # game-specific CSS file (e.g. "sheet-litm.css")

    # ---- helpers ----------------------------------------------------------

    def theme_type(self, tid: str) -> ThemeType:
        """Look up a theme type by id. Falls back to the first declared type
        so unrecognised ids degrade gracefully."""
        for t in self.theme_types:
            if t.id == tid:
                return t
        return self.theme_types[0]

    @property
    def default_theme_type_id(self) -> str:
        return self.theme_types[0].id


# ---------------------------------------------------------------------------
# Legend in the Mist
# ---------------------------------------------------------------------------

LITM = GameProfile(
    id="litm",
    name="Legend in the Mist",
    theme_types=[
        ThemeType(id="origin",    label="Origin",    color="#3f5c2f", icon="origin.svg",    banner="header-origin.webp"),
        ThemeType(id="adventure", label="Adventure", color="#7a1f1f", icon="adventure.svg", banner="header-adventure.webp"),
        ThemeType(id="greatness", label="Greatness", color="#4a2f60", icon="greatness.svg", banner="header-greatness.webp"),
    ],
    tracks=[
        Track(id="abandon",   label="Abandon"),
        Track(id="improve",   label="Improve"),
        Track(id="milestone", label="Milestone"),
    ],
    backpack_label="Backpack",
    backpack_icon="backpack.svg",
    fellowship_label="Fellowship Relationship",
    fellowship_companion_label="Companion",
    fellowship_tag_label="Relationship Tag",
    has_promise=True,
    promise_label="Promise",
    promise_size=5,
    background="bg-yellow-old-paper-textures.webp",
    stylesheet="",                     # base sheet.css already encodes LitM styling
)


# ---------------------------------------------------------------------------
# Otherscape
# ---------------------------------------------------------------------------
# Three theme types: Self / Noise / Mythos in red / blue / purple.
# Each theme's "quest" field is named differently — Identity / Itch / Ritual —
# so the form label and sheet rendering switch based on theme type.
# Two tracks (no milestones): Upgrade and Decay.

OTHERSCAPE = GameProfile(
    id="otherscape",
    name="Otherscape",
    theme_types=[
        ThemeType(id="self",   label="Self",   color="#d01c58", icon="self.png",   banner="header-self.webp",   tag_bar="select-bar-self.webp",   quest_label="Identity"),
        ThemeType(id="noise",  label="Noise",  color="#02b7cc", icon="noise.png",  banner="header-noise.webp",  tag_bar="select-bar-noise.webp",  quest_label="Itch"),
        ThemeType(id="mythos", label="Mythos", color="#7452a2", icon="mythos.png", banner="header-mythos.webp", tag_bar="select-bar-mythos.webp", quest_label="Ritual"),
    ],
    tracks=[
        Track(id="upgrade", label="Upgrade"),
        Track(id="decay",   label="Decay"),
    ],
    backpack_label="Loadout",
    backpack_icon="loadout.svg",
    fellowship_label="Crew Relationships",
    fellowship_companion_label="Crew Member",
    fellowship_tag_label="Relationship Tag",
    fellowship_icon="crew.svg",
    burn_icon="burn-neutral-empty.svg",
    weakness_bar="select-bar-weakness.webp",
    has_promise=False,
    background="bg-otherscape-metallic.webp",
    stylesheet="sheet-otherscape.css",
)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

GAMES: dict[str, GameProfile] = {
    LITM.id:        LITM,
    OTHERSCAPE.id:  OTHERSCAPE,
}

DEFAULT_GAME_ID = "litm"


def get_game(game_id: str | None) -> GameProfile:
    """Look up a game profile, defaulting to LitM for unknown / missing ids."""
    return GAMES.get(game_id or DEFAULT_GAME_ID, LITM)
