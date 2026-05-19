"""Minimal Flask app that wraps the character sheet builder.

Routes:
  GET  /                    → editor form (optionally pre-loaded with ?load=name)
  POST /preview             → returns rendered sheet HTML (for iframe embed)
  POST /pdf                 → returns rendered sheet PDF as a download
  POST /save                → saves the form payload to characters/<slug>.json
  GET  /characters          → JSON list of saved characters

The form posts a flat dict; we reconstruct the nested Character/Theme objects
in `_character_from_form`. This keeps the HTML form simple and avoids needing
JS just to manage the data shape.
"""
from __future__ import annotations

import io
import re
from pathlib import Path

from flask import Flask, render_template, request, send_file, jsonify, abort

from .models import Character, Theme, MightLevel
from .render import render_sheet_html, render_sheet_pdf

ROOT = Path(__file__).resolve().parent.parent
CHARACTERS_DIR = ROOT / "characters"


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(ROOT / "templates"),
        static_folder=str(ROOT / "static"),
    )

    # ---- editor ------------------------------------------------------------

    @app.route("/")
    def editor():
        load = request.args.get("load")
        character = Character()
        if load:
            path = CHARACTERS_DIR / f"{_slug(load)}.json"
            if path.exists():
                character = Character.load(path)
        # Ensure at least 4 themes so the form always renders 4 cards.
        while len(character.themes) < 4:
            character.themes.append(Theme())
        # List of saved character slugs to populate the "Open" dropdown.
        CHARACTERS_DIR.mkdir(parents=True, exist_ok=True)
        saved = sorted(p.stem for p in CHARACTERS_DIR.glob("*.json"))
        return render_template(
            "editor.html",
            character=character,
            might_levels=list(MightLevel),
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
            tmp_path = ROOT / "_tmp.pdf"
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
        path = CHARACTERS_DIR / f"{slug}.json"
        character.save(path)
        return jsonify({"ok": True, "slug": slug, "path": str(path.relative_to(ROOT))})

    @app.route("/characters")
    def list_characters():
        CHARACTERS_DIR.mkdir(parents=True, exist_ok=True)
        files = sorted(p.stem for p in CHARACTERS_DIR.glob("*.json"))
        return jsonify(files)

    return app


# -- helpers ----------------------------------------------------------------


def _slug(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def _character_from_form(form) -> Character:
    """Reconstruct a Character from the flat editor form.

    Variable-length lists are submitted as sequentially-indexed keys
    (e.g. theme0_power_0, theme0_power_1, ...). We iterate while keys
    exist rather than assuming a fixed count, so the user can add/remove
    rows in the editor without the server needing to know the count.
    """
    themes = []
    for i in range(4):
        p = f"theme{i}_"
        themes.append(
            Theme(
                might_level=MightLevel(form.get(f"{p}might_level", "adventure")),
                category=form.get(f"{p}category", ""),
                title=form.get(f"{p}title", ""),
                quest=form.get(f"{p}quest", ""),
                power_tags=_collect_indexed(form, f"{p}power_", limit=9),
                weakness_tags=_collect_indexed(form, f"{p}weakness_", limit=2),
                quest_description=form.get(f"{p}quest_description", ""),
                special_improvements=_collect_indexed(form, f"{p}special_", limit=10),
                abandon_pips=int(form.get(f"{p}abandon_pips", 0) or 0),
                improve_pips=int(form.get(f"{p}improve_pips", 0) or 0),
                milestone_pips=int(form.get(f"{p}milestone_pips", 0) or 0),
            )
        )
    return Character(
        name=form.get("name", ""),
        descriptor=form.get("descriptor", ""),
        quote=form.get("quote", ""),
        portrait_path=form.get("portrait_path") or None,
        backpack=[form.get(f"backpack_{k}", "") for k in range(10)],
        fellowship_companions=[form.get(f"fellowship_companion_{k}", "") for k in range(5)],
        fellowship_tags=[form.get(f"fellowship_tag_{k}", "") for k in range(5)],
        promise_pips=int(form.get("promise_pips", 0) or 0),
        themes=themes,
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
