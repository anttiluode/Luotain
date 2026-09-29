@echo off
rem Luotain overnight run (Windows).
rem Gives every still-unsettled five-multiplication law another look with long
rem Vampire limits, then refreshes results\, README.md and site\index.html.
rem Run it from anywhere; it works in the folder it lives in. Nothing is committed.

setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

rem ---- settings you may change ------------------------------------------------
rem SECONDS : finite-model searches get this long, proof attempts twice as long
rem MINUTES : total budget; laws not reached keep their old status
set SECONDS=30
set MINUTES=600

rem ---- Python -----------------------------------------------------------------
set "PY="
where python3.13 >nul 2>nul && set "PY=python3.13"
if not defined PY where py >nul 2>nul && set "PY=py -3"
if not defined PY set "PY=python"
echo Python: %PY%
%PY% -c "import numpy" 2>nul || %PY% -m pip install --user -r requirements.txt || goto :fail

rem ---- Vampire for Windows (vampire.exe + cygwin1.dll into tools\) -------------
if not exist tools\vampire.exe (
  echo Downloading Vampire 5.1.0 for Windows...
  if not exist tools mkdir tools
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://github.com/vprover/vampire/releases/download/v5.1.0/vampire-Windows-X64.zip' -OutFile 'tools\vampire.zip'; Expand-Archive -Force 'tools\vampire.zip' 'tools'; Remove-Item 'tools\vampire.zip'" || goto :fail
)
tools\vampire.exe --version || goto :fail

rem ---- fingerprints (committed; only recomputed if missing, about 15 min) -------
if not exist data\fingerprints\responses_2.npz (
  %PY% scripts\fingerprints.py || goto :fail
)

rem ---- workers: all logical processors but one ---------------------------------
set /a W=%NUMBER_OF_PROCESSORS%-1
if %W% LSS 1 set W=1

rem ---- the long run -------------------------------------------------------------
echo.
echo Started %date% %time%
%PY% scripts\place.py --retry --seconds %SECONDS% --workers %W% --max-minutes %MINUTES% || goto :fail
echo Finished %date% %time%

rem ---- refresh everything that is built from the log ------------------------------
%PY% scripts\place.py --report > results\overnight_report.txt || goto :fail
%PY% scripts\findings.py > nul || goto :fail
%PY% scripts\readme_results.py > nul || goto :fail
%PY% scripts\build_map.py || goto :fail

echo.
echo Done. New verdicts were appended to results\place_log.jsonl.
echo Summary: results\overnight_report.txt, results\order5_summary.json, README.md, site\index.html
echo Commit them when you are happy with the numbers.
pause
exit /b 0

:fail
echo.
echo Something failed; the messages above say where.
pause
exit /b 1
