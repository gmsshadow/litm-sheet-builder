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
from typing import Callable


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
    tag_bar: str = ""        # selection-bar image for power tags / title (Otherscape) — used for ACTIVE power tags + the always-active title
    tag_bar_inactive: str = ""   # paired "burn" variant of tag_bar used for INACTIVE power tags (Otherscape). Empty for games that don't distinguish.
    tally_icon: str = ""     # coloured icon for the theme-type tally column (falls back to `icon` if empty)
    quest_label: str = "Quest"   # what this theme's motto field is called (LitM: always "Quest", Otherscape: per-theme)


@dataclass(frozen=True)
class Track:
    """A 0–3 pip track on each theme (Abandon, Improve, etc.)."""
    id: str          # internal identifier ("abandon", "improve", "milestone", "decay", "upgrade")
    label: str       # display label ("Abandon", "Decay")


@dataclass(frozen=True)
class Essence:
    """A character-level essence: the archetype implied by which theme types
    a character carries, together with its special rule.

    Otherscape derives a character's essence from the *mix* of Self / Noise /
    Mythos themes they hold — e.g. holding at least one of each makes you a
    Nexus. `matches()` encodes that rule as a predicate over the per-type
    counts so `calculate_essence()` can pick the right one without a pile of
    branching logic at the call site.
    """
    id: str                  # internal identifier stored in JSON ("nexus", "cyborg", ...)
    title: str               # display title, rendered in caps on the sheet ("NEXUS")
    special: str             # the essence's special rule text
    # Predicate over a {theme_type_id: count} mapping. Returns True when this
    # essence applies to that spread of themes.
    matches: Callable[[dict[str, int]], bool] = field(default=lambda counts: False, compare=False)
    # When two essences match the same counts (Conduit vs Avatar, which are
    # distinguished by Source rather than by theme count), the one with the
    # lower sort_priority wins the automatic calculation; the other stays
    # selectable from the dropdown.
    sort_priority: int = 0


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
    tag_lozenge: str = ""            # icon rendered before title + power-tag text on each theme card (LitM's hollow lozenge marker). Empty disables — Otherscape leaves this blank since its tags already have the coloured selection bar as their visual anchor.
    tag_lozenge_filled: str = ""     # filled variant of tag_lozenge, rendered before ACTIVE power tags (and the always-active title) when the game uses the active/inactive tag system. LitM uses the solid diamond; empty means "use tag_lozenge for every tag regardless of active state".
    sort_tags_by_active: bool = True # whether power tags are reordered active-first on the sheet. Otherscape does (active tags float above to-burn ones); LitM keeps the authored order and only changes the diamond fill, so it sets this False.
    starting_active_tags: int = -1   # default active-tag count for characters whose JSON pre-dates power_tags_active. -1 = every tag starts active; a non-negative N = first N active, rest inactive (Otherscape uses 2 for its "two starting power tags" rule). Ignored when split_inactive_below_weakness is set (LitM uses a content-based default instead — see Character.from_dict).
    split_inactive_below_weakness: bool = False  # LitM layout: active power tags render above the weakness tag, inactive ones below it under the inactive_tags_label subheading. Otherscape keeps everything in one block above the weakness.
    inactive_tags_label: str = ""    # subheading shown above the inactive-tag section when split_inactive_below_weakness is set (LitM: "New power tags").
    loadout_slots: int = 10          # how many backpack/loadout rows to render — fewer for Otherscape, whose bars are taller per row
    has_promise: bool = True         # whether the Promise pip track is shown
    promise_label: str = "Promise"
    promise_size: int = 5            # number of promise pips
    show_theme_tally: bool = False   # show vertical "TYPE:N" tally next to portrait (Otherscape premium-sheet style)
    special_label: str = "Special improvement"  # label for the bonus-rule paragraph on each theme. LitM ships it as "Special improvement"; Otherscape rebrands to "Theme Special".
    show_quest_label: bool = False   # whether to render the per-theme quest_label (e.g. "IDENTITY" / "RITUAL" / "ITCH" for Otherscape) as a small caps title above each theme's motto. LitM doesn't show this — its mottos run unlabelled.
    has_essence: bool = False        # whether the character block carries an Essence section (Otherscape only). Essence is a character-level trait describing the mix of Self/Noise/Mythos themes, with its own special rule — LitM has no equivalent, so the whole block is gated off there.
    essences: list["Essence"] = field(default_factory=list)  # catalogue of the game's set essences, used both for the automatic calculation and to populate the editor's dropdown. Empty means no automatic system (the essence fields, if shown at all, are then free-text only).
    essence_label: str = "Essence"   # heading shown above the essence type on the sheet.
    essence_special_label: str = "Essence Special"  # label for the essence's bonus-rule paragraph — mirrors special_label but for the character-level essence rather than a single theme.

    # Asset paths
    background: str = ""             # background image filename
    stylesheet: str = ""             # game-specific CSS file (e.g. "sheet-litm.css")
    section_header: str = "header-backpack.webp"  # loadout + relationships banner
    loadout_bar: str = ""            # selection-bar image per loadout row (Otherscape)

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

    @property
    def uses_power_tag_active_toggle(self) -> bool:
        """Does this game render a distinct visual for inactive power tags
        and accordingly expose an active/inactive toggle in the editor?
        True when either (a) a theme type ships an inactive selection bar
        (Otherscape's "to-burn" tags), or (b) the game has a filled-lozenge
        variant (LitM's solid diamond for active tags). LitM's theme types
        leave tag_bar_inactive empty but it sets tag_lozenge_filled, so the
        diamond-fill mechanism turns the toggle on there too."""
        return (any(tt.tag_bar_inactive for tt in self.theme_types)
                or bool(self.tag_lozenge_filled))


# ---------------------------------------------------------------------------
# Legend in the Mist
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Otherscape essences
# ---------------------------------------------------------------------------
# A character's essence follows from which theme types they hold. The rules
# below read the per-type counts (how many Self / Noise / Mythos themes) and
# pick the matching archetype. Conduit and Avatar share the same count
# signature (Mythos only) and are told apart by whether the Mythos themes
# draw on the same Source - something the sheet can't infer, so Conduit wins
# the automatic pick and Avatar remains selectable from the dropdown.

def _c(counts: dict[str, int], key: str) -> int:
    """Count of themes of one type, defaulting to 0."""
    return counts.get(key, 0)


OTHERSCAPE_ESSENCES: list[Essence] = [
    Essence(
        id="nexus",
        title="Nexus",
        special=(
            "When you next replace a theme, if you're still a Nexus after the transformation, "
            "it starts as a full theme, not a nascent one."
        ),
        matches=lambda c: _c(c, "self") >= 1 and _c(c, "noise") >= 1 and _c(c, "mythos") >= 1,
    ),
    Essence(
        id="spiritualist",
        title="Spiritualist",
        special=(
            "Once per session, you can tap this bond to add your Mythos to the Power of an "
            "action that is primarily powered by Self themes, or add your Self to an action "
            "that is primarily powered by Mythos themes, or, if you are already rolling with "
            "Mythos or with Self, roll with both."
        ),
        matches=lambda c: _c(c, "self") >= 1 and _c(c, "mythos") >= 1 and _c(c, "noise") == 0,
    ),
    Essence(
        id="cyborg",
        title="Cyborg",
        special=(
            "You can add your number of Self or Noise to the Power of any action to resist or "
            "shake off mythical forces that are not manifested as tangible or measurable "
            "effects, such as curses, hallucinations, or mental influences. You may do this "
            "once per session with your Self and once per session with your Noise, or you may "
            "use both in the same action."
        ),
        matches=lambda c: _c(c, "self") >= 1 and _c(c, "noise") >= 1 and _c(c, "mythos") == 0,
    ),
    Essence(
        id="transhuman",
        title="Transhuman",
        special=(
            "Once per scene, when you invoke both mythical and technological tags in the same "
            "action, no matter their source, you can trade a miss (6 or less) outcome with a "
            "mixed hit (7-9)."
        ),
        matches=lambda c: _c(c, "mythos") >= 1 and _c(c, "noise") >= 1 and _c(c, "self") == 0,
    ),
    Essence(
        id="real",
        title="Real",
        special=(
            "Whenever you take action to directly uphold or protect one of your Identities, "
            "you may roll with Self instead of counting positive tags."
        ),
        matches=lambda c: _c(c, "self") >= 1 and _c(c, "noise") == 0 and _c(c, "mythos") == 0,
    ),
    Essence(
        id="singularity",
        title="Singularity",
        special=(
            "You can interface with ALL information, regardless of medium, and may roll with "
            "Noise to search it and, if it is recorded information, to manipulate it."
        ),
        matches=lambda c: _c(c, "noise") >= 1 and _c(c, "self") == 0 and _c(c, "mythos") == 0,
    ),
    # Conduit and Avatar share the "Mythos only" signature. Conduit is the
    # default automatic pick (sort_priority 0); Avatar (priority 1) is chosen
    # manually when the character's Mythos themes all stem from one Source.
    Essence(
        id="conduit",
        title="Conduit",
        special=(
            "You may replace themes at will as long as you replace them with a Mythos theme. "
            "Any Source in your possession or even nearby can become your new Mythos theme and "
            "it begins as a full theme, not a nascent one."
        ),
        matches=lambda c: _c(c, "mythos") >= 1 and _c(c, "self") == 0 and _c(c, "noise") == 0,
        sort_priority=0,
    ),
    Essence(
        id="avatar",
        title="Avatar",
        special="While you are an Avatar, you may instantly recover burned power tags.",
        matches=lambda c: _c(c, "mythos") >= 1 and _c(c, "self") == 0 and _c(c, "noise") == 0,
        sort_priority=1,
    ),
]


def calculate_essence(game: "GameProfile", theme_type_ids):
    """Pick the essence implied by a character's theme types.

    `theme_type_ids` is any iterable of theme-type id strings (typically
    `[t.theme_type for t in character.themes]`). Blank ids are ignored so a
    half-filled sheet doesn't skew the result.

    Returns None when the game has no essence system, when the character has
    no themes yet, or when the spread matches no rule (e.g. a Noise-only
    character, which the published essence list doesn't cover) - the caller
    then renders nothing rather than inventing an archetype.
    """
    if not game.essences:
        return None
    counts: dict[str, int] = {}
    for tid in theme_type_ids:
        if tid:
            counts[tid] = counts.get(tid, 0) + 1
    if not counts:
        return None
    matching = [e for e in game.essences if e.matches(counts)]
    if not matching:
        return None
    # Lowest sort_priority wins ties (Conduit over Avatar).
    return sorted(matching, key=lambda e: e.sort_priority)[0]


def get_essence(game: "GameProfile", essence_id: str):
    """Look up one essence by id, or None if not found / not applicable."""
    if not essence_id or not game.essences:
        return None
    for e in game.essences:
        if e.id == essence_id:
            return e
    return None


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
    tag_lozenge="litm-att-empty.svg",
    tag_lozenge_filled="litm-att-filled.svg",
    sort_tags_by_active=False,
    starting_active_tags=0,
    split_inactive_below_weakness=True,
    inactive_tags_label="New power tags",
    loadout_slots=8,
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
        ThemeType(id="self",   label="Self",   color="#d01c58", icon="self.png",   banner="header-self.webp",   tag_bar="select-bar-self.webp",   tag_bar_inactive="select-bar-self-toburn.webp",     tally_icon="self-color.png",   quest_label="Identity"),
        ThemeType(id="noise",  label="Noise",  color="#02b7cc", icon="noise.png",  banner="header-noise.webp",  tag_bar="select-bar-noise.webp",  tag_bar_inactive="select-bar-noise-toburn.webp",    tally_icon="noise-color.png",  quest_label="Itch"),
        ThemeType(id="mythos", label="Mythos", color="#7452a2", icon="mythos.png", banner="header-mythos.webp", tag_bar="select-bar-mythos.webp", tag_bar_inactive="select-bar-mythosOS-toburn.webp", tally_icon="mythos-color.png", quest_label="Ritual"),
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
    loadout_slots=8,
    has_promise=False,
    show_theme_tally=True,
    special_label="Theme Special",
    show_quest_label=True,
    has_essence=True,
    essences=OTHERSCAPE_ESSENCES,
    essence_label="Essence",
    essence_special_label="Essence Special",
    starting_active_tags=2,
    background="bg-otherscape-tokyo.webp",
    stylesheet="sheet-otherscape.css",
    section_header="header-crew.webp",
    loadout_bar="select-bar-neutral-toburn.webp",
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
