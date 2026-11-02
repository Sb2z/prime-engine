@echo off
rem ── Prime Analyst momentum intraday, 12h & 23h, lancé par le Planificateur ──
cd /d "%~dp0.."
if exist research\PAUSE (
  echo %date% %time% PAUSE present - analyst annule >> research\analyst.log
  exit /b 0
)
set PYTHONUTF8=1
set PY=%LOCALAPPDATA%\Programs\Python\Python313\python.exe
"%PY%" windows\run_analyst_wrapper.py >> research\analyst.log 2>&1
