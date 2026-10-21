@echo off
rem Double-click to start RealEstate. The first run installs what it needs.
cd /d "%~dp0"

rem Find Python: the py launcher, python on PATH, or the usual install folders
rem (Python is often installed without being added to PATH).
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do if exist "%%D\python.exe" set "PY="%%D\python.exe""
if not defined PY for /d %%D in ("%ProgramFiles%\Python3*") do if exist "%%D\python.exe" set "PY="%%D\python.exe""
if not defined PY for /d %%D in ("C:\Python3*") do if exist "%%D\python.exe" set "PY="%%D\python.exe""
if not defined PY (
    echo Could not find Python on this computer.
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
