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
        return render_template(
            "editor.html",
            character=character,
            might_levels=list(MightLevel),
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

    Field naming convention:
      name, descriptor, quote, portrait_path
      backpack_0 … backpack_5
      theme<i>_<field>  (i = 0..3)
        theme<i>_might_level
        theme<i>_category
        theme<i>_title
        theme<i>_motto
        theme<i>_power_0/1/2
        theme<i>_weakness
        theme<i>_new_power_0
        theme<i>_quest_description
        theme<i>_special_improvement
        theme<i>_abandon_pips
        theme<i>_improve_pips
        theme<i>_milestone_pips
    """
    themes = []
    for i in range(4):
        p = f"theme{i}_"
        themes.append(
            Theme(
                might_level=MightLevel(form.get(f"{p}might_level", "adventure")),
                category=form.get(f"{p}category", ""),
                title=form.get(f"{p}title", ""),
                motto=form.get(f"{p}motto", ""),
                power_tags=[form.get(f"{p}power_{k}", "") for k in range(3)],
                weakness_tag=form.get(f"{p}weakness", ""),
                new_power_slots=[form.get(f"{p}new_power_{k}", "") for k in range(1)],
                quest_description=form.get(f"{p}quest_description", ""),
                special_improvement=form.get(f"{p}special_improvement", ""),
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
        backpack=[form.get(f"backpack_{k}", "") for k in range(6)],
        themes=themes,
    )
