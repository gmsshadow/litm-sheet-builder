@echo off
setlocal enabledelayedexpansion
rem ===========================================================================
rem  Mist Engine Sheet Builder - Windows launcher.
rem
rem  Double-click this file. On first launch it builds a private Python
rem  virtual environment in this folder and installs the required packages;
rem  later launches reuse it and start quickly. The app opens in your default
rem  web browser. Close this window to quit.
rem
rem  Requires: Python 3.10+  (https://www.python.org/downloads/ - tick
rem  "Add Python to PATH" during install).
rem
rem  For PDF export, WeasyPrint needs the GTK runtime libraries on Windows.
rem  See the "Windows PDF export" note in PACKAGING.md for the one-time
rem  installer link.
rem ===========================================================================

cd /d "%~dp0"

set "VENV_DIR=%~dp0.venv"
set "PYTHON="

rem -- Locate a Python 3 interpreter. Prefer the "py" launcher, then python.
where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3 -c "import sys; sys.exit(0 if sys.version_info>=(3,10) else 1)" >nul 2>nul
  if !ERRORLEVEL!==0 set "PYTHON=py -3"
)
if not defined PYTHON (
  where python >nul 2>nul
  if !ERRORLEVEL!==0 (
    python -c "import sys; sys.exit(0 if sys.version_info>=(3,10) else 1)" >nul 2>nul
    if !ERRORLEVEL!==0 set "PYTHON=python"
  )
)

if not defined PYTHON (
  echo ERROR: Python 3.10 or newer was not found.
  echo Install it from https://www.python.org/downloads/ -- be sure to tick
  echo "Add Python to PATH" during installation -- then run this again.
  echo.
  pause
  exit /b 1
)

rem -- Create the virtual environment on first run.
if not exist "%VENV_DIR%\Scripts\python.exe" (
  echo First-time setup: creating a private Python environment...
  %PYTHON% -m venv "%VENV_DIR%"
  if !ERRORLEVEL! neq 0 (
    echo ERROR: failed to create the virtual environment.
    pause
    exit /b 1
  )
  echo Installing dependencies ^(this happens only once^)...
  "%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip >nul
  "%VENV_DIR%\Scripts\python.exe" -m pip install -r "%~dp0requirements.txt"
  if !ERRORLEVEL! neq 0 (
    echo ERROR: failed to install dependencies.
    pause
    exit /b 1
  )
)

echo.
echo Starting the Sheet Builder. Your browser should open shortly.
echo If it doesn't, visit:  http://127.0.0.1:5000
echo Close this window to quit.
echo.

"%VENV_DIR%\Scripts\python.exe" "%~dp0run.py"

rem If the server exits with an error, keep the window open so the user can read it.
if %ERRORLEVEL% neq 0 pause
endlocal
