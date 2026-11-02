@echo off
rem ── Session chercheur nocturne (23h30), équivalent research/run_nightly.sh ──
cd /d "%~dp0.."
set PYTHONUTF8=1
if exist research\PAUSE (
  echo %date% %time% PAUSE present - session annulee >> research\nightly.log
  exit /b 0
)
set PY=%LOCALAPPDATA%\Programs\Python\Python313\python.exe
"%PY%" windows\run_nightly_wrapper.py >> research\nightly.log 2>&1
