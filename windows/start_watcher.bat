@echo off
rem ── PRIME WATCHER — lancé par le Planificateur de tâches au démarrage ──
rem Superviseur de relance (équivalent systemd Restart=always / RestartSec=30) :
rem si prime_watcher.py sort (crash), on attend 30s — le temps que le verrou
rem DuckDB se libère — puis on relance. Auto-cicatrisation d'un crash de process,
rem pas seulement d'un reboot. Les évènements START/EXIT vont dans
rem watcher_supervisor.log (PAS prime_watcher.log) pour ne pas fausser la
rem détection mtime du watchdog (silence >12 min sur prime_watcher.log).
cd /d C:\Users\sam\trading
set PYTHONUTF8=1
rem chemin complet : la tache tourne en SYSTEM, dont le PATH ignore l'install Python par-utilisateur
set PY=C:\Users\samue\AppData\Local\Programs\Python\Python313\python.exe
:loop
echo %date% %time% START prime_watcher >> watcher_supervisor.log
"%PY%" -u prime_watcher.py >> prime_watcher.log 2>&1
echo %date% %time% EXIT prime_watcher (code %ERRORLEVEL%) -- relance dans 30s >> watcher_supervisor.log
ping -n 31 127.0.0.1 >nul
goto loop
