#!/usr/bin/env python3
"""WATCHDOG — détecte un watcher mort, gelé OU en crash-loop.

Le risque couvert : le prime_watcher plante/gèle et le silence Telegram
ressemble à "pas de setup" alors que c'est "système éteint". Lancé toutes les
15 min.

DURCI 2026-06-16 : on ne se fie plus au seul mtime de prime_watcher.log (un
crash-loop réécrit le log à chaque retry → mtime frais → faux OK ; un gel
laisse le mtime vieillir mais c'est ambigu). Le VRAI signal de santé est la
fraîcheur du DERNIER CYCLE réel (event type=cycle dans le jsonl) + la présence
du process. On distingue ainsi : process absent (mort), process vivant mais ne
cycle plus (gel / crash-loop). Si le watcher est franchement MORT (aucun
process prime_watcher.py), on tente une relance auto (schtasks /Run) en plus de
l'alerte — le superviseur start_watcher.bat couvre déjà le crash de python ;
ceci couvre le cas où le superviseur lui-même a disparu.

Anti-spam : une alerte par épisode, rappel toutes les 2h max. Alerte de
rétablissement quand les cycles reviennent.
"""

import datetime as dt
import json
import os
import subprocess

import notify

LOG_FILE = "/Users/sam/trading/prime_watcher.log"
EVENTS_FILE = "/Users/sam/trading/prime_watcher_events.jsonl"
STATE_FILE = "/Users/sam/trading/watchdog_state.json"
STALE_AFTER_S = 12 * 60
REMIND_EVERY_S = 2 * 3600
WATCHER_TASK = "Prime Watcher"


def _last_cycle_age(now):
    """Âge (s) du dernier cycle RÉEL (event type=cycle), lu en fin de jsonl."""
    try:
        size = os.path.getsize(EVENTS_FILE)
        with open(EVENTS_FILE, "rb") as f:
            f.seek(max(0, size - 65536))
            tail = f.read().decode("utf-8", "ignore")
    except FileNotFoundError:
        return float("inf")
    last_ts = None
    for line in tail.splitlines():
        if '"type": "cycle"' in line or '"type":"cycle"' in line:
            try:
                last_ts = json.loads(line).get("ts")
            except Exception:
                pass
    if not last_ts:
        return float("inf")
    try:
        t = dt.datetime.fromisoformat(last_ts.replace("Z", "+00:00")).timestamp()
        return now - t
    except Exception:
        return float("inf")


def _python_count():
    """Nombre de process python.exe (tasklist : toujours présent, lisible par
    SYSTEM, contrairement à wmic/commandline qui est inaccessible sur un process
    SYSTEM et déprécié en 25H2). Sert de garde-fou SÛR pour la relance auto :
    on ne relance QUE si 0 python (aucun détenteur du verrou DuckDB → aucun
    risque de double-lancement). None si indéterminable."""
    try:
        # PAS text=True : tasklist sort en codepage OEM (FR), pas UTF-8 →
        # UnicodeDecodeError sur 0xff. On capture les octets et on décode en
        # ignorant (python.exe + PID sont ASCII, seul ce dont on a besoin).
        raw = subprocess.run(
            ["tasklist", "/fi", "imagename eq python.exe", "/fo", "csv", "/nh"],
            capture_output=True, timeout=15).stdout or b""
        out = raw.decode("utf-8", "ignore")
        me = os.getpid()                      # exclure le watchdog lui-même
        n = 0
        for ln in out.splitlines():
            if "python.exe" not in ln.lower():
                continue
            parts = [p.strip().strip('"') for p in ln.split(",")]
            try:
                if int(parts[1]) == me:
                    continue
            except (IndexError, ValueError):
                pass
            n += 1
        return n
    except Exception:
        return None


def _try_restart():
    try:
        subprocess.run(["schtasks", "/Run", "/TN", WATCHER_TASK],
                       capture_output=True, timeout=20)
        return True
    except Exception:
        return False


def main():
    now = dt.datetime.now(dt.timezone.utc).timestamp()
    cycle_age = _last_cycle_age(now)          # signal de santé principal
    nproc = _python_count()

    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
    except Exception:
        state = {"silent": False, "last_alert": 0}

    if cycle_age > STALE_AFTER_S:
        if nproc == 0:
            diag = "AUCUN process python (système à terre)"
            if not state.get("silent"):       # une seule relance auto par épisode
                diag += " → relance auto " + ("OK" if _try_restart() else "ÉCHEC")
        else:
            npart = "?" if nproc is None else str(nproc)
            diag = (f"{npart} python présent(s) mais aucun cycle frais "
                    "(gel ou crash-loop) — intervention requise")
        if not state["silent"] or now - state["last_alert"] > REMIND_EVERY_S:
            age_txt = "jamais" if cycle_age == float("inf") else f"{cycle_age/60:.0f} min"
            notify.send(
                f"⚠️ WATCHER MUET — dernier cycle il y a {age_txt} — {diag}. "
                f"Le silence n'est pas 'pas de setup', c'est 'système en panne'.")
            state = {"silent": True, "last_alert": now}
    elif state.get("silent"):
        notify.send("✅ Watcher de nouveau actif (cycles frais).", silent=True)
        state = {"silent": False, "last_alert": 0}

    # Disque : à ~90% d'occupation, un gros consommateur externe (Windows Update,
    # dump...) peut asphyxier la machine et donc le watcher. Alerte sous 15 Go,
    # même anti-spam que l'alerte watcher (une fois par épisode, rappel 2h).
    try:
        import shutil
        free_gb = shutil.disk_usage("C:/").free / 1024**3
        if free_gb < 15:
            if not state.get("disk_alert") or now - state.get("disk_last", 0) > REMIND_EVERY_S:
                notify.send(f"⚠️ DISQUE C: {free_gb:.0f} Go libres (<15) — risque "
                            f"d'asphyxie du pipeline, fais du ménage.")
                state["disk_alert"] = True
                state["disk_last"] = now
        elif state.get("disk_alert"):
            state["disk_alert"] = False
    except Exception:
        pass

    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


if __name__ == "__main__":
    main()
