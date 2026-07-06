@echo off
rem ── Briefing de tendance (signal-only), 5x/jour, lancé par le Planificateur ──
cd /d C:\Users\sam\trading
set PYTHONUTF8=1
set PY=C:\Users\samue\AppData\Local\Programs\Python\Python313\python.exe
"%PY%" market_brief.py >> market_brief.log 2>&1
