"""Path resolution that works both from source and inside a PyInstaller bundle.

Two distinct roots matter:

* **resource root** — read-only assets shipped with the program (templates,
  static fonts/images/css). When frozen by PyInstaller these are unpacked into
  a temporary directory exposed as ``sys._MEIPASS``; from source they live in
  the project tree.

* **data root** — the writable location for things the user creates or edits,
  i.e. the ``characters/`` library and any rendered output. When frozen this
  must live *next to the executable* (the _MEIPASS temp dir is wiped on exit and
  is read-only in practice), so saved characters persist between runs. From
  source it's just the project root.

Keeping these separate is what lets the same codebase run unmodified as a
``python run.py`` checkout, as a bootstrapped-venv launcher, and as a frozen
single-file executable.
"""
from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    """True when running inside a PyInstaller (or similar) bundle."""
    return bool(getattr(sys, "frozen", False))


def resource_root() -> Path:
    """Directory containing read-only bundled resources (templates, static).

    Frozen: the PyInstaller extraction dir (``sys._MEIPASS``).
    Source: the project root (parent of the ``core`` package).
    """
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parent.parent


def data_root() -> Path:
    """Directory for writable user data (the ``characters/`` library).

    Frozen: the folder the executable sits in, so saves persist and the user
    can find their files next to the app.
    Source: the project root, matching the original on-disk layout.
    """
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def templates_dir() -> Path:
    return resource_root() / "templates"


def static_dir() -> Path:
    return resource_root() / "static"


def characters_dir() -> Path:
    """Writable characters library. Created on first access if missing, and
    seeded from any characters bundled alongside the resources (so a fresh
    frozen install still ships with the sample characters)."""
    target = data_root() / "characters"
    if not target.exists():
        target.mkdir(parents=True, exist_ok=True)
        _seed_characters(target)
    return target


def portraits_dir() -> Path:
    """Writable directory for user-uploaded portrait images. Sits alongside
    the characters/ library so that saved characters and their portraits
    live in the same visible place on disk — a user opening the app's
    folder sees both. Auto-created on first access; never seeded (users
    supply their own portraits via the editor's file picker)."""
    target = data_root() / "portraits"
    target.mkdir(parents=True, exist_ok=True)
    return target


def output_dir() -> Path:
    """Writable directory for rendered PDFs.

    Sits beside characters/ and portraits/ in the data root, so a user who
    opens the app's folder finds their saved characters, the portraits they
    imported, and the sheets they exported in three obvious places rather
    than having exports scattered through a browser download history.
    Auto-created on first access; never seeded.

    Callers must tolerate this raising OSError: when the app is installed
    somewhere the user can't write to (Program Files, /opt), the export is
    still expected to succeed via the browser download, just without the
    archived copy.
    """
    target = data_root() / "output"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _seed_characters(target: Path) -> None:
    """Copy bundled sample characters into a freshly-created data dir.

    Only runs when the writable characters dir didn't already exist, so it
    never clobbers a user's saved files. No-op when the bundled and target
    dirs are the same path (running from source).
    """
    bundled = resource_root() / "characters"
    if not bundled.exists() or bundled.resolve() == target.resolve():
        return
    import shutil
    for item in bundled.rglob("*"):
        if item.is_file():
            dest = target / item.relative_to(bundled)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dest)
