# Legend in the Mist — Sheet Builder

A small Flask + WeasyPrint app for designing and exporting character sheets for
*Legend in the Mist* in a layout close to the published premade sheets, using
free font/asset substitutes so the result can be redistributed and customised.

## What's in the skeleton

```
litm-sheet-builder/
├── run.py                         # entry point (web app + CLI)
├── requirements.txt
├── litm/
│   ├── models.py                  # Character, Theme, MightLevel dataclasses
│   ├── render.py                  # HTML + PDF rendering via Jinja and WeasyPrint
│   └── app.py                     # Flask routes (editor, preview, /pdf, /save)
├── templates/
│   ├── editor.html                # the form, with live <iframe> preview
│   └── sheet.html                 # the actual character sheet (one file does
│                                  # double duty for browser preview and PDF)
├── static/
│   ├── css/
│   │   ├── editor.css             # form UI
│   │   └── sheet.css              # all of the visual fidelity lives here
│   ├── icons/                     # placeholder SVGs (leaf, sword, crown, lantern)
│   ├── images/                    # drop character portraits here
│   └── fonts/                     # drop font files here, then wire @font-face in sheet.css
└── characters/
    └── roen-stillhand.json        # sample character to verify the pipeline
```

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python run.py
# → open http://127.0.0.1:5000
```

Headless PDF rendering:

```bash
python run.py pdf characters/roen-stillhand.json
# → writes characters/roen-stillhand.pdf
```

## WeasyPrint platform notes

WeasyPrint is a pure-Python renderer but it binds to native libraries
(Pango, Cairo, gdk-pixbuf, libffi) which need to be installed at the OS level.

- **Debian/Ubuntu**: `sudo apt install libpango-1.0-0 libpangoft2-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 libffi-dev`
- **macOS (Homebrew)**: `brew install pango cairo gdk-pixbuf libffi`
- **Windows**: see <https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#windows>

If WeasyPrint won't install in your environment, the rest of the app still
works — the `/pdf` route will return an error message but `/preview` will
keep rendering the HTML sheet. A pragmatic fallback is to open the preview
HTML in Chrome and use *File → Print → Save as PDF*; the same `sheet.css`
controls the output either way.

## Three Might levels, three banner styles

Themes are tagged with one of:

| level       | banner colour    | icon  | CSS modifier        |
|-------------|------------------|-------|---------------------|
| `origin`    | forest green     | leaf  | `.theme--origin`    |
| `adventure` | oxblood red      | sword | `.theme--adventure` |
| `greatness` | deep purple      | crown | `.theme--greatness` |

Pick the right one in the editor's *Might level* dropdown; the colour scheme
and icon update automatically. The Might level also drives the colour of
filled track pips and the power-tag borders inside each theme card.

## Visual fidelity ladder

The skeleton lands you at **"recognisable from across the table"**. The
following levers close the remaining gap, in roughly increasing order of
effort:

1. **Add real character portraits.** Drop a PNG in `static/images/` and
   reference it from the *Portrait path* field (e.g. `images/roen.png`).
2. **Bundle the free display fonts locally.** Download
   [Cinzel Decorative](https://fonts.google.com/specimen/Cinzel+Decorative),
   [IM Fell English](https://fonts.google.com/specimen/IM+Fell+English) and
   [EB Garamond](https://fonts.google.com/specimen/EB+Garamond) into
   `static/fonts/`, then add matching `@font-face` blocks at the top of
   `static/css/sheet.css`. WeasyPrint will then embed them in the PDF and
   the result will look the same on any machine.
3. **Swap the radial-gradient parchment for a real paper texture.** Save
   a paper PNG to `static/images/parchment.jpg`, then in `sheet.css`:

   ```css
   body.sheet-page {
     background: var(--paper) url("../images/parchment.jpg") center/cover;
   }
   ```

4. **Refine the icons.** The four SVGs in `static/icons/` are deliberately
   simple — replace with custom artwork or sourced icons under a compatible
   licence (e.g. game-icons.net, CC-BY).
5. **Tighten the theme card layout.** Tweak `.theme__banner`, `.tag`, and the
   pip tracks to taste — every visual is exposed as a CSS class.

## On copyright

The published sheets are © Son of Oak Game Studio. This builder reproduces
the **functional layout** (portrait, themes, tracks, backpack) and uses free
substitutes for fonts, icons, and texture so anything you generate is yours
to distribute. The "How to Play" block in `templates/sheet.html` ships with
generic placeholder rules text; replace it with your own paraphrase rather
than copying from the rulebook.

## What's intentionally not here yet

- Active-effects style automation (mark progress → auto-fill pip)
- Image upload via the form (right now you drop files into `static/images/`)
- Multi-page sheets, NPC sheets, or location/threat sheets
- A bundled paper texture or display font (licensing left to the user)

These are easy to layer on top — the data model and rendering pipeline are
already factored to support them.
