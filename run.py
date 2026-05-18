"""Entry point.

Usage:
    python run.py                       # launch the web editor at http://127.0.0.1:5000
    python run.py pdf <character.json>  # render a saved character JSON to PDF
"""
from __future__ import annotations

import sys
from pathlib import Path

from litm.app import create_app
from litm.models import Character
from litm.render import render_sheet_pdf


def _cli_pdf(json_path: str, out_path: str | None = None) -> None:
    src = Path(json_path)
    character = Character.load(src)
    out = Path(out_path) if out_path else src.with_suffix(".pdf")
    render_sheet_pdf(character, out)
    print(f"Wrote {out}")


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "pdf":
        if len(sys.argv) < 3:
            sys.exit("usage: python run.py pdf <character.json> [out.pdf]")
        _cli_pdf(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
        return
    app = create_app()
    # debug=True gives template auto-reload; safe for local dev only.
    app.run(host="127.0.0.1", port=5000, debug=True)


if __name__ == "__main__":
    main()
