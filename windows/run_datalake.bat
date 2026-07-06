@echo off
rem ── Refresh quotidien du data lake (07h00) — lancé en SYSTEM ──
cd /d C:\Users\sam\trading
set PYTHONUTF8=1
set PY=C:\Users\samue\AppData\Local\Programs\Python\Python313\python.exe
"%PY%" research\datalake.py refresh >> research\datalake.log 2>&1
