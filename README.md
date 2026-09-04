# Mist Engine Sheet Builder

A local Flask + WeasyPrint app for designing and exporting character sheets for
the Mist Engine games — **Legend in the Mist** and **:Otherscape** — in a layout
close to the published premade sheets, using free font and asset substitutes so
whatever you generate is yours to redistribute.

It runs as a small web server on your own machine: you fill in a form, watch a
live preview of the sheet update beside it, then export a print-ready PDF.

---

## Quickstart

**Just want to run it?** Double-click `run.bat` (Windows) or `./run.sh`
(Linux/macOS). On first launch they build a private virtual environment next to
the script and install the dependencies; later launches start in a second or
two. See [PACKAGING.md](PACKAGING.md) for the standalone no-Python-required
builds.

**From source:**

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python run.py
# → opens http://127.0.0.1:5000
```

**Headless PDF rendering** (handy for regenerating a batch of sheets):

```bash
python run.py pdf characters/otherscape/vex.json
# → writes characters/otherscape/vex.pdf

python run.py pdf characters/litm/roen-stillhand.json out/roen.pdf
```

Environment variables recognised by `run.py` and the launchers:

| Variable | Effect |
|----------|--------|
| `LITM_PORT` | Port for the local server (default `5000`) |
| `LITM_DEBUG` | `1` enables Flask debug + auto-reload (development only) |
| `LITM_NO_BROWSER` | `1` skips auto-opening the browser |

---

## The two games

Everything game-specific lives in a `GameProfile` in `core/games.py`. The
templates and CSS are generic and consult the profile, so the same editor and
the same sheet template render both games.

| | Legend in the Mist | :Otherscape |
|---|---|---|
| Theme types | Origin / Adventure / Greatness | Self / Noise / Mythos |
| Tracks | Abandon, Improve, Milestone | Upgrade, Decay |
| Motto field | *Quest* (unlabelled on the sheet) | *Identity* / *Itch* / *Ritual* (labelled) |
| Inventory | Backpack | Loadout |
| Group block | Fellowship Relationship | Crew Relationships |
| Promise track | Yes (5 pips) | No |
| Theme tally | No | Yes — vertical `TYPE:N` spine |
| Essence | No | Yes, with an isometric theme-mix diagram |
| Tag styling | Hollow / solid diamond lozenges | Coloured selection bars + "to burn" variants |
| Look | Aged paper, serif display type | Neon-on-dark Tokyo, chunky display type |

Adding a third Mist Engine game means writing one more `GameProfile` and
registering it in `GAMES` — no template or CSS surgery required.

---

## Features

- **Live editor** — a form with an embedded `<iframe>` preview that re-renders
  the real sheet as you type, so what you see is what prints.
- **Four theme cards**, each with a type, category, title, motto, 2–9 power
  tags, 1–2 weakness tags, an open-ended list of special improvements, and the
  game's pip tracks.
- **Active / to-burn power tags.** Each tag carries an active flag. Otherscape
  floats active tags to the top of the card and renders the rest with the
  "burn" variant of the selection bar; LitM keeps the authored order and splits
  inactive ones into a *New power tags* section below the weakness.
- **Essence (Otherscape).** Resolved through three tiers — a free-text custom
  override, an explicit pick from the dropdown, or automatic calculation from
  the character's mix of theme types (Nexus, Cyborg, Spiritualist, Transhuman,
  Real, Singularity, Conduit / Avatar).
- **Essence diagram (Otherscape).** The isometric cube-in-a-hexagon from the
  published cards, generated as inline SVG from the same theme counts the tally
  spine prints. Mythos is the left wall, Noise the right wall, Self the floor;
  each sector fills outward from the centre, one shell per theme of that type.
- **Portrait upload** through the editor's file picker, stored in a writable
  `portraits/` folder beside your saved characters.
- **Page backdrops.** Each game has a full-bleed background per orientation —
  a Tokyo cityscape for Otherscape, and for Legend in the Mist a landscape
  vista sitting behind a parchment veil (`--vista-veil` in `sheet.css` sets
  how strongly the art reads against the ink).
- **Landscape or portrait orientation.** Landscape gives the classic wide
  layout; portrait switches to a 2×2 grid of theme cards with more vertical
  room per card and a wider portrait column.
- **JSON character library** under `characters/<game>/`, with transparent
  migration of older schemas so nothing you saved months ago stops loading.
- **PDF export** via WeasyPrint, plus a standalone HTML path that prints
  identically from a browser if WeasyPrint isn't available.

---

## Project layout

```
├── run.py                          # entry point: web app + `pdf` CLI
├── run.bat / run.sh                # zero-install launchers (bootstrap a venv)
├── build_windows.bat / build_linux.sh
├── mist_engine_sheet_builder.spec  # PyInstaller spec → Mist-Engine-Sheet-Builder
├── requirements.txt
├── core/
│   ├── games.py                    # GameProfile, ThemeType, Track, Essence, plus
│   │                               #   the LITM and OTHERSCAPE profiles — the one
│   │                               #   place game-specific knowledge lives
│   ├── models.py                   # Character / Theme dataclasses + schema migration
│   ├── essence_diagram.py          # isometric theme-mix diagram → inline SVG
│   ├── render.py                   # Jinja + WeasyPrint rendering
│   ├── app.py                      # Flask routes
│   └── paths.py                    # source-vs-frozen resource/data root resolution
├── templates/
│   ├── editor.html                 # the form, with live preview
│   └── sheet.html                  # the sheet — one file serves preview and PDF
├── static/
│   ├── css/
│   │   ├── editor.css
│   │   ├── sheet.css               # shared layout + LitM styling
│   │   └── sheet-otherscape.css    # Otherscape overrides layered on top
│   └── icons/  images/  fonts/
└── characters/
    ├── litm/                       # roen-stillhand.json, bumbler.json
    └── otherscape/                 # vex.json, wilson.json
```

Two path roots keep the same code working from a checkout and from a frozen
build (`core/paths.py`): a **resource root** for read-only bundled assets, and a
**data root** for the writable `characters/` and `portraits/` folders. In a
standalone build the data root sits next to the executable, so saves persist and
users can find their files.

---

## WeasyPrint platform notes

WeasyPrint is pure Python but binds to native libraries (Pango, Cairo,
gdk-pixbuf, libffi) that must be installed at the OS level:

- **Debian/Ubuntu** — `sudo apt install libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libffi8`
- **Fedora** — `sudo dnf install pango cairo gdk-pixbuf2`
- **macOS (Homebrew)** — `brew install pango cairo gdk-pixbuf libffi`
- **Windows** — install the [GTK3 runtime](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases) and put its `bin\` directory on `PATH`

If WeasyPrint won't install, the rest of the app still works: `/pdf` reports
that export is unavailable while the preview keeps rendering. The fallback is to
open the preview in Chrome and use *File → Print → Save as PDF* — the same CSS
drives both.

For the standalone builds these libraries must be present on the **build**
machine so PyInstaller can detect and copy them. See
[PACKAGING.md](PACKAGING.md).

---

## Releases

Tagged GitHub Releases are built automatically by
`.github/workflows/build.yml`, which produces and attaches:

- `Mist-Engine-Sheet-Builder-windows-x64.zip`
- `Mist-Engine-Sheet-Builder-linux-x64.zip`

Each unzips to a `Mist-Engine-Sheet-Builder/` folder containing the executable
of the same name. No Python required. Both jobs smoke-test the built binary by
rendering a PDF, so a broken bundle fails the build rather than shipping.

---

## On copyright

The published sheets are © Son of Oak Game Studio. This builder reproduces the
**functional layout** — portrait, themes, tags, tracks, loadout, relationships —
and uses free substitutes for fonts, icons and textures, so the sheets you
generate are yours to distribute. Rules text you enter is your own; don't paste
in rulebook copy you intend to share.

---

## Not there yet

- Automation (mark progress → auto-fill a pip)
- NPC, location, threat or challenge sheets
- Multi-page sheets for characters with more than four themes
- A localisation layer for non-English play

The data model and rendering pipeline are factored to take all of these; each is
additive rather than a rewrite.
