"""HTML and PDF rendering for character sheets.

The same Jinja template (`sheet.html`) is used for the on-screen preview and
for the PDF export. WeasyPrint reads the static CSS via the `base_url` we pass
in, so paths like `static/css/sheet.css` resolve identically in both contexts.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .games import get_game
from .models import Character
from .paths import resource_root, templates_dir, static_dir

ROOT = resource_root()
TEMPLATES = templates_dir()
STATIC = static_dir()


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_sheet_html(character: Character, *, embed_css: bool = False) -> str:
    """Render the character sheet as a standalone HTML page.

    Resolves the game profile from the character so the template can access
    game-specific labels, asset paths, and theme-type metadata.
    """
    env = _env()
    template = env.get_template("sheet.html")
    game = get_game(character.game)
    css_inline: Optional[str] = None
    if embed_css:
        # Inline the base sheet CSS plus the game-specific stylesheet.
        base = (STATIC / "css" / "sheet.css").read_text(encoding="utf-8")
        game_css = (STATIC / "css" / game.stylesheet).read_text(encoding="utf-8") if game.stylesheet else ""
        css_inline = base + "\n\n" + game_css
    return template.render(
        character=character,
        game=game,
        standalone=True,
        css_inline=css_inline,
    )


def render_sheet_pdf(character: Character, output_path: str | Path) -> Path:
    """Render to PDF on disk via WeasyPrint. Returns the output Path.

    WeasyPrint is an optional dependency; we import it lazily so the rest of
    the app (form editor, JSON IO) still works on systems where the native
    Pango/Cairo deps haven't been installed yet.
    """
    try:
        from weasyprint import HTML  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "WeasyPrint is not installed. Install it with `pip install weasyprint` "
            "and ensure system libs (pango, cairo, gdk-pixbuf) are present. "
            "See README.md for platform-specific notes."
        ) from e

    html = render_sheet_html(character, embed_css=False)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # base_url lets relative paths like /static/... resolve against the project root.
    HTML(string=html, base_url=str(ROOT)).write_pdf(target=str(output_path))
    return output_path
