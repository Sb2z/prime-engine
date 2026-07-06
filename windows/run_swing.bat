@echo off
rem ── Signal hebdo SWING ACTIONS (achat/vente) -> Telegram ──
cd /d C:\Users\sam\trading
set PYTHONUTF8=1
rem chemin complet : tache SYSTEM, PATH sans le Python par-utilisateur
set PY=C:\Users\samue\AppData\Local\Programs\Python\Python313\python.exe
"%PY%" swing_book.py send >> swing_book.log 2>&1
