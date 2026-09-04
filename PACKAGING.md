# Packaging & Distribution

There are two ways to ship this program. Pick based on whether your users have
Python installed.

| Approach | User needs Python? | Effort | Best for |
|----------|:------------------:|--------|----------|
| **A. Launcher scripts** (`run.bat` / `run.sh`) | Yes (3.10+) | Zero build step | Quick sharing, technical users, your own machines |
| **B. Standalone build** (PyInstaller `.exe` / binary) | No | Build once per OS | Sharing with non-technical users |
| **C. Automated builds** (GitHub Actions) | No | Push a release | Hands-off `.exe` + Linux binary on every release |

Both produce the same app: a small local web server that opens in the browser.
The window stays open while you use it; close it to quit.

---

## A. Launcher scripts (no build needed)

Ship the whole project folder. The user runs the launcher for their OS:

- **Windows** — double-click **`run.bat`**
- **Linux / macOS** — run **`./run.sh`** (first: `chmod +x run.sh`)

On first launch the script creates a private virtual environment (`.venv/`)
inside the folder, installs the dependencies, then starts the app and opens the
browser. Later launches reuse the environment and start in a second or two.

This requires Python 3.10+ on the user's machine. The launcher checks for it and
prints a download link if it's missing.

---

## B. Standalone executable (PyInstaller)

This bundles Python and every dependency into a folder the user just unzips and
runs — no Python required. **PyInstaller does not cross-compile**, so you build
on the OS you're targeting: build the Windows `.exe` on Windows, the Linux
binary on Linux.

### Build on Linux
```bash
./build_linux.sh
```
Output: `dist/Mist-Engine-Sheet-Builder/` — launch with
`./dist/Mist-Engine-Sheet-Builder/Mist-Engine-Sheet-Builder`. Zip that folder to distribute.

### Build on Windows
```bat
build_windows.bat
```
Output: `dist\Mist-Engine-Sheet-Builder\Mist-Engine-Sheet-Builder.exe`. Zip the
`dist\Mist-Engine-Sheet-Builder\` folder to distribute.

Both wrappers just set up a clean build venv and run
`pyinstaller mist_engine_sheet_builder.spec`. The spec produces a **one-dir** build (a
folder, not a single file) — it starts faster and is far more reliable for
WeasyPrint than one-file.

The build is large (~250–300 MB) because it includes Python, WeasyPrint, and the
font/graphics libraries. That's normal for a bundled WeasyPrint app.

User saves persist: on first run the app copies the bundled sample characters
into a writable `characters/` folder next to the executable, and all future
saves go there.

---

## C. Automated builds via GitHub Actions

`.github/workflows/build.yml` builds **both** the Windows `.exe` and the Linux
binary on GitHub's runners, so you never need a Windows machine yourself.

**To cut a release:**
1. Push your code to GitHub.
2. Create a Release (Releases → Draft a new release → pick a tag like `v1.0.0`
   → Publish).
3. The workflow runs two jobs in parallel — one on `ubuntu-latest`, one on
   `windows-latest` — and attaches `Mist-Engine-Sheet-Builder-linux-x64.zip`
   and `Mist-Engine-Sheet-Builder-windows-x64.zip` to that release
   automatically.

You can also trigger it by hand (Actions → "Build standalone executables" →
Run workflow); manual runs upload the zips as workflow **artifacts** instead of
attaching them to a release.

Each job installs the GTK/Pango libraries WeasyPrint needs (via `apt` on Linux,
via MSYS2's mingw-w64 packages on Windows), runs the same
`mist_engine_sheet_builder.spec`, then **smoke-tests** the built binary by
rendering a PDF — so a broken bundle fails the build instead of shipping.

> **Note on the Windows GTK step:** bundling Pango/Cairo on Windows is the one
> part that can be finicky across runner-image updates. If a future Windows
> build fails to find the GTK DLLs, the fix is almost always in the "Put GTK
> DLLs on PATH" step of the workflow — adjust the mingw64 path or pin the MSYS2
> package versions.

---

The editor, preview, and JSON save/load work with pure-Python packages. **PDF
export** uses [WeasyPrint](https://weasyprint.org/), which renders text through
native Pango/Cairo libraries. Those are the one thing that isn't pure Python, so
they need to be present:

### Linux PDF export
Install the system libraries once (the launcher and the PDF feature both use
them):
```bash
# Debian / Ubuntu
sudo apt install libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libffi8
# Fedora
sudo dnf install pango cairo gdk-pixbuf2
# macOS (Homebrew)
brew install pango gdk-pixbuf libffi
```
For a **standalone Linux build**, these must be present on the *build* machine
so PyInstaller can detect and copy them into the bundle.

### Windows PDF export
WeasyPrint on Windows needs the **GTK3 runtime**. Install it once from the
[GTK-for-Windows runtime installer](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases)
and make sure its `bin\` directory is on `PATH`.

- For the **launcher** approach, the *end user* installs the GTK runtime if they
  want PDF export (the editor still works without it).
- For the **standalone build**, the GTK runtime must be on `PATH` on *your build
  machine* so PyInstaller bundles the DLLs; users of the resulting `.exe` then
  need nothing extra.

If WeasyPrint isn't available, the app still runs — only the "Download PDF"
button reports that PDF export is unavailable, with the same guidance.

---

## What gets shipped

The launcher approach ships the project tree. The standalone build ships
`dist/Mist-Engine-Sheet-Builder/`. In both cases these folders are bundled and
don't need to be edited by users:

```
templates/   static/   core/   characters/ (seed)   run.py   requirements.txt
```

Build artifacts (`build/`, `dist/`, `.venv/`, `.build-venv/`) are throwaway and
should not be committed or shipped as source.
