@echo off
rem Double-click to start RealEstate. The first run installs what it needs.
cd /d "%~dp0"

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY (
    echo Python is not installed.
    echo Install it from https://www.python.org/downloads/ and tick "Add python.exe to PATH",
    echo then double-click start.bat again.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo First run: setting up, this takes a minute...
    %PY% -m venv .venv || goto :failed
)
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -e . || goto :failed

".venv\Scripts\python.exe" -m realestate.web --open
exit /b 0

:failed
echo.
echo Setup failed. See the message above.
pause
exit /b 1
