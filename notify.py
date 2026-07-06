#!/usr/bin/env python3
"""NOTIFY, alertes Telegram du Prime Engine.

Token et chat_id dans .env (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, jamais en
clair dans le repo). Sans credentials, send() est un no-op silencieux : le
watcher ne casse pas, le log reste la source fiable.

Utilisé par le watcher pour : A_SETUP Prime, trend-day armé, fenêtre
pré-event, résumé quotidien. SIGNAL-ONLY : aucune action de trading, jamais.
"""

import datetime
import json
import os
import urllib.parse
import urllib.request

ENV = "/Users/sam/trading/.env"
OUTBOX = "/Users/sam/trading/telegram_outbox.jsonl"  # copie locale de TOUT envoi
STATE = "/Users/sam/trading/telegram_state.json"     # compteur d'échecs consécutifs


def _key(name):
    v = os.environ.get(name)
    if v:
        return v.strip()
    try:
        for line in open(ENV):
            if line.strip().startswith(name):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return None


def _log_outbox(text, silent, ok):
    """Copie locale append-only de TOUT message envoyé (relecture/analyse par
    l'analyste : cohérence des alertes vs état interne, bugs de format, etc.).
    Ne casse JAMAIS l'envoi ; rotation légère au-delà de ~1 Mo (2000 dernières)."""
    try:
        rec = {"ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "ok": bool(ok), "silent": bool(silent), "text": text}
        with open(OUTBOX, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        if os.path.getsize(OUTBOX) > 1_000_000:
            with open(OUTBOX, encoding="utf-8") as f:
                tail = f.readlines()[-2000:]
            with open(OUTBOX, "w", encoding="utf-8") as f:
                f.writelines(tail)
    except Exception:
        pass


def _bump_failures(ok, configured):
    """Suivi des échecs d'envoi CONSÉCUTIFS (API joignable mais refus/timeout).
    N'incrémente PAS quand les credentials manquent (no-op volontaire, pas un échec).
    À la reprise après >=1 échec, logge un marqueur dans l'outbox -> Sam sait qu'il a
    raté des alertes. Persisté (survit au caractère par-appel de send). Jamais bloquant."""
    if not configured:
        return
    try:
        try:
            st = json.load(open(STATE))
        except Exception:
            st = {}
        n = int(st.get("consecutive_failures", 0))
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if ok:
            if n > 0:
                _log_outbox(f"♻️ Telegram rétabli après {n} échec(s) d'envoi consécutif(s).", True, True)
            st = {"consecutive_failures": 0, "last_ok_ts": now}
        else:
            st = {"consecutive_failures": n + 1, "last_fail_ts": now}
        json.dump(st, open(STATE, "w"))
    except Exception:
        pass


def consecutive_failures():
    """Nombre d'échecs d'envoi consécutifs actuels (0 si tout va bien). Pour le
    résumé quotidien / watchdog : savoir si le canal Telegram est devenu muet."""
    try:
        return int(json.load(open(STATE)).get("consecutive_failures", 0))
    except Exception:
        return 0


def send(text, silent=False, timeout=10):
    """Envoie un message Telegram ET en garde une copie locale (OUTBOX).
    Retourne True si accepté par l'API."""
    token = _key("TELEGRAM_BOT_TOKEN")
    chat_id = _key("TELEGRAM_CHAT_ID")
    ok = False
    if token and chat_id:
        try:
            data = urllib.parse.urlencode({
                "chat_id": chat_id,
                "text": text[:4000],
                "disable_notification": "true" if silent else "false",
            }).encode()
            req = urllib.request.Request(
                f"https://api.telegram.org/bot{token}/sendMessage", data=data)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                ok = bool(json.loads(r.read().decode()).get("ok"))
        except Exception:
            ok = False
    _log_outbox(text, silent, ok)
    _bump_failures(ok, bool(token and chat_id))
    return ok


if __name__ == "__main__":
    ok = send("✅ Prime Engine, canal d'alerte Telegram opérationnel.\n"
              "Tu recevras ici : A_SETUP, mode scalp-tendance, pré-event macro, "
              "résumé quotidien. Signal-only, aucune exécution automatique.")
    print("envoi:", "OK" if ok else "ÉCHEC (credentials manquants ou API)")
