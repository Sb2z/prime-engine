"""Wrapper timeout 45 min de la session chercheur (portable Windows).

Blindé le 12/06/2026 après l'échec FileNotFoundError du 11/06 23:30 (spawn
refusé dans le contexte de la tâche planifiée alors que l'exe existait) :
candidats multiples, diagnostic d'environnement en cas d'échec, et un retry
60 s plus tard.
"""
import datetime
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # dossier du projet

PROMPT = """Tu es le chercheur nocturne du Prime Research Lab. Lis et applique
strictement research/RESEARCH_PROTOCOL.md (cycle: ingestion, autopsie, max 3
hypothèses nouvelles, expériences via harness.evaluate, rapport
research/reports/{date}.md + résumé Telegram 5 lignes via notify.send
silent=True). Tu n'écris QUE dans research/. Commit final de tes fichiers
research/ avec un message clair.""".format(date=datetime.date.today().isoformat())

CANDIDATES = [
    os.path.expandvars(r"%APPDATA%\npm\node_modules\@anthropic-ai\claude-code\bin\claude.exe"),
    os.path.expandvars(r"%USERPROFILE%\.local\bin\claude.exe"),
    os.path.expandvars(r"%USERPROFILE%\AppData\Roaming\npm\node_modules\@anthropic-ai\claude-code\bin\claude.exe"),
]


def log(msg):
    print(f"{datetime.datetime.now():%F %T}, {msg}", flush=True)


exe = next((c for c in CANDIDATES if os.path.isfile(c)), None)
log(f"session chercheur démarrée (exe={exe})")
if exe is None:
    log(f"AUCUN claude trouvé parmi : {CANDIDATES}")
    sys.exit(2)

rc = 3
for attempt in (1, 2):
    try:
        r = subprocess.run(
            [exe, "-p", PROMPT, "--permission-mode", "acceptEdits", "--max-turns", "80",
             "--settings", os.path.join(ROOT, ".claude", "autonomous_settings.json")],
            timeout=45 * 60, cwd=ROOT, stdin=subprocess.DEVNULL)
        rc = r.returncode
        break
    except subprocess.TimeoutExpired:
        log("TIMEOUT 45 min, session interrompue (budget)")
        rc = 124
        break
    except OSError as exc:
        log(f"échec du lancement (tentative {attempt}/2) : {type(exc).__name__} {exc}")
        log(f"diag: USERNAME={os.environ.get('USERNAME')} "
            f"USERPROFILE={os.environ.get('USERPROFILE')} "
            f"exe_existe={os.path.isfile(exe)} cwd_existe={os.path.isdir(ROOT)}")
        if attempt == 1:
            time.sleep(60)

log(f"session terminée (exit {rc})")
sys.exit(rc)
