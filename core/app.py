"""Flask app — game-aware.

Routes:
  GET  /?game=<id>&load=<slug>    → editor form (game-specific, optionally pre-loaded)
  POST /preview                   → returns rendered sheet HTML (for iframe embed)
  POST /pdf                       → returns rendered sheet PDF as a download
  POST /save                      → saves to characters/<game>/<slug>.json
  GET  /characters?game=<id>      → JSON list of saved characters for the game

The form posts a flat dict; we reconstruct the nested Character/Theme objects
in `_character_from_form`. Variable-length lists are submitted as sequentially-
indexed keys (theme0_power_0, theme0_power_1, ...) and the parser iterates
while keys exist.
"""
from __future__ import annotations

import io
import re
from pathlib import Path

from flask import Flask, render_template, request, send_file, jsonify, abort

from .games import GAMES, get_game, DEFAULT_GAME_ID
from .models import Character, Theme
from .render import render_sheet_html, render_sheet_pdf
from .paths import templates_dir, static_dir, characters_dir

# Writable characters library — resolves next to the executable when frozen,
# or the project root from source. Created/seeded on first access.
CHARACTERS_DIR = characters_dir()


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(templates_dir()),
        static_folder=str(static_dir()),
    )

    # ---- editor ------------------------------------------------------------

    @app.route("/")
    def editor():
        load = request.args.get("load")
        game_id = request.args.get("game") or DEFAULT_GAME_ID
        game = get_game(game_id)

        character = Character(game=game.id)
        # If a load slug is given, look it up in this game's characters dir.
        # If the slug isn't found in this game but exists in another, redirect-style:
        # we just load whatever we find so the user isn't stuck.
        if load:
            path = _character_path(game.id, load)
            if path.exists():
                character = Character.load(path)
            else:
                # Fall back: search other games. Useful when a user passes ?load=slug
                # without ?game= and we want to find the character anywhere.
                for other in GAMES.values():
                    candidate = _character_path(other.id, load)
                    if candidate.exists():
                        character = Character.load(candidate)
                        game = get_game(character.game)
                        break

        # Ensure exactly 4 themes so the form always renders 4 cards. New themes
        # default to the game's first theme type.
        while len(character.themes) < 4:
            character.themes.append(Theme(theme_type=game.default_theme_type_id))

        # List saved characters for this game (drives the Open dropdown).
        game_dir = CHARACTERS_DIR / game.id
        game_dir.mkdir(parents=True, exist_ok=True)
        saved = sorted(p.stem for p in game_dir.glob("*.json"))

        return render_template(
            "editor.html",
            character=character,
            game=game,
            games=list(GAMES.values()),
            saved_characters=saved,
            current_slug=_slug(character.name) if load else "",
        )

    # ---- preview / export --------------------------------------------------

    @app.route("/preview", methods=["POST"])
    def preview():
        character = _character_from_form(request.form)
        return render_sheet_html(character, embed_css=False)

    @app.route("/pdf", methods=["POST"])
    def pdf():
        character = _character_from_form(request.form)
        slug = _slug(character.name) or "character"
        buf = io.BytesIO()
        try:
            # Render to a scratch file in the OS temp dir (the resource root is
            # read-only when frozen), then stream its bytes back to the client.
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
                tmp_path = Path(tf.name)
            render_sheet_pdf(character, tmp_path)
            buf.write(tmp_path.read_bytes())
            tmp_path.unlink(missing_ok=True)
        except RuntimeError as e:
            return (str(e), 500)
        buf.seek(0)
        return send_file(
            buf,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"{slug}.pdf",
        )

    # ---- persistence -------------------------------------------------------

    @app.route("/save", methods=["POST"])
    def save():
        character = _character_from_form(request.form)
        slug = _slug(character.name)
        if not slug:
            abort(400, "Character needs a name before saving.")
        path = _character_path(character.game, slug)
        character.save(path)
        # Report a friendly relative path (relative to the characters library).
        try:
            rel = str(path.relative_to(CHARACTERS_DIR.parent))
        except ValueError:
            rel = str(path)
        return jsonify({"ok": True, "slug": slug, "game": character.game, "path": rel})

    @app.route("/characters")
    def list_characters():
        game_id = request.args.get("game") or DEFAULT_GAME_ID
        game = get_game(game_id)
        game_dir = CHARACTERS_DIR / game.id
        game_dir.mkdir(parents=True, exist_ok=True)
        files = sorted(p.stem for p in game_dir.glob("*.json"))
        return jsonify(files)

    return app


# -- helpers ----------------------------------------------------------------


def _slug(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def _character_path(game_id: str, slug: str) -> Path:
    return CHARACTERS_DIR / game_id / f"{_slug(slug)}.json"


def _character_from_form(form) -> Character:
    """Reconstruct a Character from the flat editor form."""
    game_id = form.get("game") or DEFAULT_GAME_ID
    game = get_game(game_id)

    themes = []
    for i in range(4):
        p = f"theme{i}_"
        # Build the pips dict from whatever track ids the game defines, falling
        # back to 0 if the form didn't supply that track (e.g. game switched).
        pips = {
            tr.id: int(form.get(f"{p}pip_{tr.id}", 0) or 0)
            for tr in game.tracks
        }
        # Collect the special-improvement text rows first, then read the
        # parallel filled-state checkboxes for each row. Unchecked checkboxes
        # don't submit at all (HTML form behaviour), so we can't iterate them
        # the way _collect_indexed iterates text fields — we walk the same
        # index range that special_improvements occupies and ask whether the
        # matching checkbox key is present.
        special_improvements = _collect_indexed(form, f"{p}special_", limit=10)
        special_improvements_filled = [
            bool(form.get(f"{p}special_filled_{k}"))
            for k in range(len(special_improvements))
        ]
        # Same pattern for power-tag active state: walk the same index range
        # as power_tags and ask whether each `power_active_K` checkbox is in
        # the form. Unchecked = inactive (the user can toggle a previously-
        # active tag off and have it persist as False). For games that don't
        # surface this toggle (LitM), default to all-active so the LitM
        # editor's missing checkboxes don't accidentally flip every tag
        # inactive on save — the field still round-trips through the JSON,
        # it just never has reason to be False.
        power_tags = _collect_indexed(form, f"{p}power_", limit=9)
        if game.uses_power_tag_active_toggle:
            power_tags_active = [
                bool(form.get(f"{p}power_active_{k}"))
                for k in range(len(power_tags))
            ]
        else:
            power_tags_active = [True] * len(power_tags)
        themes.append(
            Theme(
                theme_type=form.get(f"{p}theme_type", game.default_theme_type_id),
                category=form.get(f"{p}category", ""),
                title=form.get(f"{p}title", ""),
                quest=form.get(f"{p}quest", ""),
                power_tags=power_tags,
                power_tags_active=power_tags_active,
                weakness_tags=_collect_indexed(form, f"{p}weakness_", limit=2),
                quest_description=form.get(f"{p}quest_description", ""),
                special_improvements=special_improvements,
                special_improvements_filled=special_improvements_filled,
                pips=pips,
            )
        )
    # `orientation` round-trips through the form so a portrait sheet stays
    # portrait when re-saved. Anything outside the allowed pair degrades to
    # "landscape" — same fallback the JSON loader applies on disk.
    orientation = form.get("orientation", "landscape")
    if orientation not in ("landscape", "portrait"):
        orientation = "landscape"

    return Character(
        name=form.get("name", ""),
        descriptor=form.get("descriptor", ""),
        quote=form.get("quote", ""),
        portrait_path=form.get("portrait_path") or None,
        backpack=[form.get(f"backpack_{k}", "") for k in range(game.loadout_slots)],
        backpack_active=(
            [bool(form.get(f"backpack_active_{k}")) for k in range(game.loadout_slots)]
            if game.uses_power_tag_active_toggle else
            [False] * game.loadout_slots
        ),
        fellowship_companions=[form.get(f"fellowship_companion_{k}", "") for k in range(5)],
        fellowship_tags=[form.get(f"fellowship_tag_{k}", "") for k in range(5)],
        promise_pips=int(form.get("promise_pips", 0) or 0),
        themes=themes,
        game=game.id,
        orientation=orientation,
    )


def _collect_indexed(form, prefix: str, limit: int = 99) -> list[str]:
    """Pull `<prefix>0`, `<prefix>1`, ... from the form, stopping at the first
    missing index or when `limit` is hit. Trailing empties are preserved so
    the user's row count round-trips through the form correctly."""
    out: list[str] = []
    for i in range(limit):
        key = f"{prefix}{i}"
        if key not in form:
            break
        out.append(form.get(key, ""))
    return out
