"""Wrapper de la session PRIME ANALYST (momentum intraday) — 12h & 23h.

Miroir durci de run_nightly_wrapper.py. Le mode (midday/evening) est déduit de
l'heure ; le timeout du soir est dimensionné pour FINIR avant le chercheur
nocturne de 23h30 (aucune collision de commit). Signal-only, constitution V3
inchangée (cf. research/ANALYST_PROTOCOL.md).

Modes :
  python run_analyst_wrapper.py        → lance la session claude -p
  python run_analyst_wrapper.py dry    → affiche slot/timeout/prompt sans lancer
"""
import datetime
import os
import subprocess
import sys
import time

CANDIDATES = [
    r"C:\Users\samue\AppData\Roaming\npm\node_modules\@anthropic-ai\claude-code\bin\claude.exe",
    os.path.expandvars(r"%USERPROFILE%\.local\bin\claude.exe"),
]


def log(m):
    print(f"{datetime.datetime.now():%F %T} — {m}", flush=True)


now = datetime.datetime.now()
slot = f"{now.hour:02d}h"
# 4 passages/jour (09h/13h/17h/23h). Seul celui de 23h doit finir AVANT le
# chercheur nocturne de 23h30 → budget plus court ; les autres ont 40 min.
timeout_min = 25 if now.hour >= 23 else 40
date = datetime.date.today().isoformat()
report = f"research/reports/analyst_{date}_{slot}.md"

PROMPT = (
    "Tu es le PRIME ANALYST — analyste momentum intraday du Research Lab. "
    f"Session {slot} ({now:%F %H:%M} Paris). Lis et applique STRICTEMENT "
    "research/ANALYST_PROTOCOL.md ET research/RESEARCH_PROTOCOL.md (cadre "
    "constitutionnel : signal-only, tu n'écris QUE dans research/, le juge "
    "harness.evaluate tranche, Sam promeut, déflation et registry inchangés, "
    "production GELÉE). Thème prioritaire : momentum de tendance appliqué en "
    "INTRADAY + confluences, jugé SANS complaisance sur la période/régime EN "
    "COURS. Scanne tout comme le programme (macro, news, technique, régime, "
    "conjoncture, trades du robot dans journal.json + prime_watcher_events.jsonl). "
    f"Écris ton rapport dans {report} (PAS le rapport nocturne daté). Vérifie la "
    "condition de RECO PROMOTION (ANALYST_PROTOCOL §4) et envoie la reco si "
    "remplie. Résumé Telegram 5 lignes via notify.send(silent=False). Commit "
    "final de tes fichiers research/."
)

if len(sys.argv) > 1 and sys.argv[1] == "dry":
    print(f"slot={slot} timeout={timeout_min}min report={report}")
    print("exe=" + str(next((c for c in CANDIDATES if os.path.isfile(c)), None)))
    print("--- PROMPT ---")
    print(PROMPT)
    sys.exit(0)

exe = next((c for c in CANDIDATES if os.path.isfile(c)), None)
log(f"analyst {slot} démarré (exe={exe}, timeout {timeout_min}min)")
if exe is None:
    log(f"AUCUN claude trouvé parmi {CANDIDATES}")
    sys.exit(2)

rc = 3
try:
    r = subprocess.run(
        [exe, "-p", PROMPT, "--permission-mode", "acceptEdits", "--max-turns", "80",
         "--settings", r"C:\Users\sam\trading\.claude\autonomous_settings.json"],
        timeout=timeout_min * 60, cwd=r"C:\Users\sam\trading", stdin=subprocess.DEVNULL)
    rc = r.returncode
except subprocess.TimeoutExpired:
    log(f"TIMEOUT {timeout_min}min — session coupée (budget)")
    rc = 124
except OSError as exc:
    log(f"échec du lancement : {type(exc).__name__} {exc}")
    rc = 3

log(f"analyst {slot} terminé (exit {rc})")
if rc != 0:
    # audit 07-02 : le créneau 09h a échoué en silence (session limit Claude) —
    # un passage de surveillance sur 4 perdu sans que personne ne le sache.
    try:
        sys.path.insert(0, r"C:\Users\sam\trading")
        import notify
        notify.send(f"⚠️ Prime Analyst {slot} en ÉCHEC (exit {rc}) — passage de "
                    f"surveillance perdu (quota/timeout ?). Voir research/analyst.log.",
                    silent=True)
    except Exception:
        pass
sys.exit(rc)
