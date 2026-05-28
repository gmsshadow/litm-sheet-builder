@echo off
setlocal
rem ===========================================================================
rem  Build a self-contained Windows executable with PyInstaller.
rem  Run this ON a Windows machine (PyInstaller does not cross-compile).
rem
rem  Output: dist\LitM-Sheet-Builder\  (zip this folder to distribute)
rem          dist\LitM-Sheet-Builder\LitM-Sheet-Builder.exe
rem
rem  Prerequisites:
rem    * Python 3.10+ on PATH
rem    * The GTK runtime, so WeasyPrint's native libraries are present for
rem      PyInstaller to detect and copy. Install the GTK3 runtime from:
rem        https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases
rem      and make sure its bin\ folder is on PATH before building.
rem      (See PACKAGING.md for the full WeasyPrint-on-Windows note.)
rem ===========================================================================

cd /d "%~dp0"

echo Setting up an isolated build environment...
python -m venv .build-venv
if %ERRORLEVEL% neq 0 ( echo ERROR: could not create build venv. & pause & exit /b 1 )

call .build-venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt pyinstaller
if %ERRORLEVEL% neq 0 ( echo ERROR: dependency install failed. & pause & exit /b 1 )

echo Building...
pyinstaller --noconfirm --clean litm_sheet_builder.spec
if %ERRORLEVEL% neq 0 ( echo ERROR: PyInstaller build failed. & pause & exit /b 1 )

echo.
echo Done. Standalone app is in:  dist\LitM-Sheet-Builder\
echo Launch it by double-clicking: dist\LitM-Sheet-Builder\LitM-Sheet-Builder.exe
echo To distribute, zip the whole dist\LitM-Sheet-Builder\ folder.
echo.
pause
endlocal
