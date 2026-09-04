"""Isometric essence diagram (Otherscape's cube-in-a-hexagon).

The official :Otherscape character cards show the character's theme mix as an
isometric "inside corner of a room": a pointy-top hexagon split by a Y from
its centre into three rhombi — a left wall, a right wall and a floor. Each
rhombus belongs to one theme type (Mythos / Noise / Self) and is filled
outward from the centre in concentric shells, one shell per theme of that
type. A character with four themes fills their sectors out to the hexagon's
edge; a type with no themes leaves its sector as bare outline.

This module turns a character's theme-type counts into a self-contained SVG
string. It is deliberately dependency-free and emits presentation attributes
rather than CSS classes, because WeasyPrint renders inline ``<svg>`` with its
own engine and does not reliably cascade the document stylesheet into it.
For the same reason there are no ``<filter>`` elements: the neon glow is
faked with a wide, low-opacity stroke sitting under a thin bright one.

Geometry
--------
Working in unit vectors from the hexagon centre::

    UP = ( 0, -1)          DL = (-√3/2, +1/2)          DR = (+√3/2, +1/2)

Each face is the rhombus spanned by two of those three axes, so a face at
radius *r* is ``[C, C+r·a, C+r·(a+b), C+r·b]``. At *r* = R the three faces
tile the hexagon exactly, which is what makes the illusion work.

Shell radii are linear but do not start at zero: on the printed cards the
innermost shell is noticeably fatter than the ones stacked outside it
(measured at roughly 0.43 R, then even steps out to 1.0 R for four themes).
`INNER_RING_FRACTION` keeps that proportion.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

SQ3_2 = math.sqrt(3) / 2.0

# Axis unit vectors, in SVG coordinates (y grows downward).
_UP = (0.0, -1.0)
_DL = (-SQ3_2, 0.5)
_DR = (SQ3_2, 0.5)

# Which pair of axes spans each face, and how bright that face is relative to
# the theme type's base colour. Walls sit "in shadow" a touch; the floor
# catches the light, matching the shading on the published cards.
_FACES: dict[str, tuple[tuple[float, float], tuple[float, float], float]] = {
    "left":  (_UP, _DL, 0.86),
    "right": (_UP, _DR, 0.96),
    "floor": (_DL, _DR, 1.06),
}

# Radius of the innermost shell as a fraction of the hexagon's circumradius.
INNER_RING_FRACTION = 0.43


@dataclass(frozen=True)
class EssenceDiagram:
    """Per-game configuration for the diagram.

    `left` / `right` / `floor` are theme-type ids from the game profile, so a
    game with three theme types can opt in simply by declaring which type
    occupies which face. `rings` is the number of theme slots a character
    has — the count that fills a sector all the way to the hexagon edge.
    """
    left: str
    right: str
    floor: str
    rings: int = 4
    frame_color: str = "#b9e02a"      # neon outline
    guide_opacity: float = 0.30       # inner ring / spoke guide lines
    glow_opacity: float = 0.22        # wide under-stroke faking the neon bloom


# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------

def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    v = value.strip().lstrip("#")
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)


def _rgb_to_hex(rgb: tuple[float, float, float]) -> str:
    return "#{:02x}{:02x}{:02x}".format(
        *(max(0, min(255, int(round(c)))) for c in rgb)
    )


def _shade(color: str, factor: float, toward_white: float = 0.0) -> str:
    """Scale a colour's brightness, then optionally mix it toward white.

    `factor` handles per-face lighting; `toward_white` handles the shell
    gradient (inner shells are washed out, outer shells are full strength).
    """
    r, g, b = _hex_to_rgb(color)
    r, g, b = r * factor, g * factor, b * factor
    if toward_white:
        r = r + (255 - r) * toward_white
        g = g + (255 - g) * toward_white
        b = b + (255 - b) * toward_white
    return _rgb_to_hex((r, g, b))


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _pt(cx: float, cy: float, r: float, *vs: tuple[float, float]) -> tuple[float, float]:
    """Centre plus r times the sum of the given axis vectors."""
    x = cx + r * sum(v[0] for v in vs)
    y = cy + r * sum(v[1] for v in vs)
    return x, y


def _points(pts) -> str:
    return " ".join(f"{x:.2f},{y:.2f}" for x, y in pts)


def _ring_radii(radius: float, rings: int) -> list[float]:
    """Shell boundary radii, index 0 being the centre (0.0).

    Returns `rings + 1` values: r[0] = 0, r[rings] = radius, with the first
    shell deliberately fatter than the rest.
    """
    if rings <= 1:
        return [0.0, radius]
    inner = radius * INNER_RING_FRACTION
    step = (radius - inner) / (rings - 1)
    return [0.0] + [inner + step * i for i in range(rings)]


def _face_polygon(cx, cy, r, a, b) -> str:
    """The full rhombus of a face at radius r (used for the innermost shell)."""
    return _points([
        (cx, cy),
        _pt(cx, cy, r, a),
        _pt(cx, cy, r, a, b),
        _pt(cx, cy, r, b),
    ])


def _band_polygon(cx, cy, r0, r1, a, b) -> str:
    """The gnomon between two concentric rhombi on the same face."""
    return _points([
        _pt(cx, cy, r0, a),
        _pt(cx, cy, r1, a),
        _pt(cx, cy, r1, a, b),
        _pt(cx, cy, r1, b),
        _pt(cx, cy, r0, b),
        _pt(cx, cy, r0, a, b),
    ])


def _hexagon(cx, cy, r) -> str:
    """Pointy-top hexagon, as the union of the three faces' outer corners."""
    return _points([
        _pt(cx, cy, r, _UP),            # top
        _pt(cx, cy, r, _UP, _DR),       # upper right
        _pt(cx, cy, r, _DR),            # lower right
        _pt(cx, cy, r, _DL, _DR),       # bottom
        _pt(cx, cy, r, _DL),            # lower left
        _pt(cx, cy, r, _UP, _DL),       # upper left
    ])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def theme_type_counts(character) -> dict[str, int]:
    """How many themes the character has of each theme type."""
    counts: dict[str, int] = {}
    for theme in getattr(character, "themes", []) or []:
        tid = getattr(theme, "theme_type", "")
        if tid:
            counts[tid] = counts.get(tid, 0) + 1
    return counts


def essence_diagram_svg(game, character, size: int = 96, padding: int = 4) -> str:
    """Render the diagram for `character` as an inline SVG string.

    Returns an empty string when the game profile has no `essence_diagram`,
    so the template can call this unconditionally and simply get nothing for
    Legend in the Mist.
    """
    cfg = getattr(game, "essence_diagram", None)
    if cfg is None:
        return ""

    counts = theme_type_counts(character)
    # A pointy-top hexagon of circumradius R is 2R tall and √3·R wide, so the
    # square viewBox is driven by the height and the width is left slack.
    radius = (size / 2.0) - padding
    cx = cy = size / 2.0
    radii = _ring_radii(radius, cfg.rings)

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" '
        f'width="{size}" height="{size}" class="essence-hex__svg" '
        f'role="img" aria-label="Theme mix">'
    ]

    # --- filled sectors ---------------------------------------------------
    for face, type_id in (("left", cfg.left), ("right", cfg.right), ("floor", cfg.floor)):
        a, b, lighting = _FACES[face]
        count = min(counts.get(type_id, 0), cfg.rings)
        if count <= 0:
            continue
        base = game.theme_type(type_id).color
        for k in range(1, count + 1):
            # Innermost shell is washed out; the outermost is full strength.
            wash = 0.34 * (1.0 - (k - 1) / max(1, cfg.rings - 1))
            fill = _shade(base, lighting, wash)
            if k == 1:
                poly = _face_polygon(cx, cy, radii[1], a, b)
            else:
                poly = _band_polygon(cx, cy, radii[k - 1], radii[k], a, b)
            parts.append(
                f'<polygon points="{poly}" fill="{fill}" '
                f'stroke="{_shade(base, lighting * 0.55)}" stroke-width="0.6"/>'
            )

    # --- guide lines: inner ring hexagons + the central Y ------------------
    guide = cfg.frame_color
    for r in radii[1:-1]:
        parts.append(
            f'<polygon points="{_hexagon(cx, cy, r)}" fill="none" stroke="{guide}" '
            f'stroke-width="0.8" stroke-opacity="{cfg.guide_opacity:.2f}"/>'
        )
    for axis in (_UP, _DL, _DR):
        x, y = _pt(cx, cy, radius, axis)
        parts.append(
            f'<line x1="{cx:.2f}" y1="{cy:.2f}" x2="{x:.2f}" y2="{y:.2f}" '
            f'stroke="{guide}" stroke-width="0.8" stroke-opacity="{cfg.guide_opacity:.2f}"/>'
        )

    # --- outer frame, with a fake glow under it ---------------------------
    outer = _hexagon(cx, cy, radius)
    parts.append(
        f'<polygon points="{outer}" fill="none" stroke="{guide}" stroke-width="4" '
        f'stroke-opacity="{cfg.glow_opacity:.2f}" stroke-linejoin="round"/>'
    )
    parts.append(
        f'<polygon points="{outer}" fill="none" stroke="{guide}" stroke-width="1.6" '
        f'stroke-linejoin="round"/>'
    )

    parts.append("</svg>")
    return "".join(parts)
