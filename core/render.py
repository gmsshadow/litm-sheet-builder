"""HTML and PDF rendering for character sheets.

The same Jinja template (`sheet.html`) is used for the on-screen preview and
for the PDF export. WeasyPrint reads the static CSS via the `base_url` we pass
in, so paths like `static/css/sheet.css` resolve identically in both contexts.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .essence_diagram import essence_diagram_svg
from .games import get_game
from .models import Character
from .paths import resource_root, templates_dir, static_dir, portraits_dir

ROOT = resource_root()
TEMPLATES = templates_dir()
STATIC = static_dir()


def _portrait_url(portrait_path: Optional[str], for_pdf: bool) -> Optional[str]:
    """Resolve a character's stored portrait_path to a URL suitable for the
    current render target.

    Two storage conventions coexist so existing character JSONs keep working
    while new uploads use the writable portraits/ directory:

    * **Uploaded** (new — no path separators in the stored string): the file
      lives in the writable ``portraits/`` dir next to the executable. For
      the browser preview we return ``/portraits/<name>`` (Flask serves it);
      for the PDF render we return an absolute ``file://`` URL so WeasyPrint
      reads it directly from disk.

    * **Bundled/legacy** (contains a slash — e.g. ``images/hero.jpg``): the
      file is under ``static/`` inside the resource root. Browser gets the
      plain ``static/<path>`` relative URL that WeasyPrint's ``base_url`` /
      Flask's static handler already resolve; PDF gets an absolute ``file://``
      URL under ``static/`` for reliability.

    Returns None when the character has no portrait set, letting the
    template render its empty-frame placeholder."""
    if not portrait_path:
        return None
    is_legacy_path = ("/" in portrait_path) or ("\\" in portrait_path)
    if is_legacy_path:
        if for_pdf:
            return (STATIC / portrait_path).as_uri()
        return f"static/{portrait_path}"
    # Uploaded file — bare filename under portraits_dir().
    if for_pdf:
        return (portraits_dir() / portrait_path).as_uri()
    return f"/portraits/{portrait_path}"


def _env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    # The essence diagram is generated markup rather than a static asset, so
    # it goes in as a global the template can call. It returns "" for games
    # whose profile has no essence_diagram, so the template needn't guard it
    # beyond the usual `{% if %}` for layout purposes.
    env.globals["essence_diagram_svg"] = essence_diagram_svg
    return env


def render_sheet_html(character: Character, *, embed_css: bool = False, for_pdf: bool = False) -> str:
    """Render the character sheet as a standalone HTML page.

    Resolves the game profile from the character so the template can access
    game-specific labels, asset paths, and theme-type metadata. Pass
    ``for_pdf=True`` when the HTML is destined for WeasyPrint — that flips
    the portrait URL to an absolute ``file://`` path so the image is read
    from disk instead of resolving against a running Flask server.
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
        portrait_url=_portrait_url(character.portrait_path, for_pdf=for_pdf),
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

    html = render_sheet_html(character, embed_css=False, for_pdf=True)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # base_url lets relative paths like /static/... resolve against the project root.
    HTML(string=html, base_url=str(ROOT)).write_pdf(target=str(output_path))
    return output_path
