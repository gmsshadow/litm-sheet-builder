"""Entry point.

Usage:
    python run.py                       # launch the web editor, opens a browser
    python run.py pdf <character.json>  # render a saved character JSON to PDF

Environment variables (used by the packaged launchers):
    LITM_PORT        port for the local server (default 5000)
    LITM_DEBUG       set to "1" to enable Flask debug/auto-reload (dev only)
    LITM_NO_BROWSER  set to "1" to skip auto-opening the browser
"""
from __future__ import annotations

import os
import sys
import threading
import webbrowser
from pathlib import Path

from core.app import create_app
from core.models import Character
from core.render import render_sheet_pdf


def _cli_pdf(json_path: str, out_path: str | None = None) -> None:
    src = Path(json_path)
    character = Character.load(src)
    out = Path(out_path) if out_path else src.with_suffix(".pdf")
    render_sheet_pdf(character, out)
    print(f"Wrote {out}")


def _open_browser_later(url: str, delay: float = 1.2) -> None:
    """Open the default browser shortly after the server starts.

    Runs on a timer thread so it fires once the server is accepting
    connections. Failures (e.g. headless box) are swallowed — the URL is also
    printed to the console as a fallback.
    """
    def _go() -> None:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    threading.Timer(delay, _go).start()


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "pdf":
        if len(sys.argv) < 3:
            sys.exit("usage: python run.py pdf <character.json> [out.pdf]")
        _cli_pdf(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
        return

    port = int(os.environ.get("LITM_PORT", "5000"))
    debug = os.environ.get("LITM_DEBUG") == "1"
    url = f"http://127.0.0.1:{port}"

    app = create_app()

    # Auto-open the browser unless disabled. Skip it when the debug reloader is
    # active, because that spawns a child process and would open two tabs;
    # only the reloader's child has WERKZEUG_RUN_MAIN set.
    want_browser = (
        os.environ.get("LITM_NO_BROWSER") != "1"
        and os.environ.get("WERKZEUG_RUN_MAIN") != "true"
    )
    if want_browser:
        print(f"Opening {url} in your browser...")
        print("Leave this window open while you use the app. Close it to quit.")
        _open_browser_later(url)

    # use_reloader is forced off when frozen - the reloader re-execs the
    # interpreter, which doesn't work inside a PyInstaller bundle.
    use_reloader = debug and not getattr(sys, "frozen", False)
    app.run(host="127.0.0.1", port=port, debug=debug, use_reloader=use_reloader)


if __name__ == "__main__":
    main()
