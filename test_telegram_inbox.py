#!/usr/bin/env python3
"""TEST telegram_inbox : parsing des commandes + capture + SÉCURITÉ (chat de Sam
uniquement). Tout mocké, aucun réseau, aucune donnée live, aucun envoi réel."""
import datetime as dt
import json
import os
import tempfile
import urllib.request
import telegram_inbox as ti
import user_trade_context
import notify

FAIL = []


def chk(n, ok, d=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {n}" + (f", {d}" if d else ""))
    if not ok:
        FAIL.append(n)


print("Parsing des commandes")
chk("T GOLD SHORT 4150", ti.parse("T GOLD SHORT 4150") == ("GOLD", "SHORT", 4150.0))
chk("TRADE xau sell 4150,5 (alias + virgule)", ti.parse("TRADE xau sell 4150,5") == ("GOLD", "SHORT", 4150.5))
chk("t SPX buy 7500 (US500 long)", ti.parse("t SPX buy 7500") == ("US500", "LONG", 7500.0))
chk("OR LONG (alias FR)", ti.parse("T OR ACHAT 4200") == ("GOLD", "LONG", 4200.0))
chk("texte libre -> None", ti.parse("bonjour ça va ?") is None)
chk("actif inconnu (BTC) -> None", ti.parse("T BTC LONG 50000") is None)
chk("prix manquant -> None", ti.parse("T GOLD SHORT") is None)

print("poll_and_capture : capture + sécurité chat")
ti.STATE = os.path.join(tempfile.gettempdir(), "_ti_state.json")
if os.path.exists(ti.STATE):
    os.remove(ti.STATE)
notify._key = lambda k: {"TELEGRAM_BOT_TOKEN": "tok", "TELEGRAM_CHAT_ID": "123"}.get(k)
calls = []
user_trade_context.capture = lambda a, d, e, ts=None, note="": (
    calls.append((a, d, e, note, ts)) or {"id": "X", "context": {"grade": "WATCH", "conf": 7, "of_imbalance": 0.1, "of_poc_dist": -0.01, "session": "NY", "regime": "RANGE"}, "context_age_min": 3})
sent = []
notify.send = lambda t, silent=False: sent.append(t)
now_epoch = int(dt.datetime.now(dt.timezone.utc).timestamp())
fake = {"ok": True, "result": [
    {"update_id": 10, "message": {"chat": {"id": 123}, "date": now_epoch, "text": "T GOLD SHORT 4150"}},
    {"update_id": 11, "message": {"chat": {"id": 999}, "date": now_epoch, "text": "T GOLD LONG 1"}},  # AUTRE chat -> ignoré
    {"update_id": 12, "message": {"chat": {"id": 123}, "date": now_epoch, "text": "coucou"}},          # pas une commande
]}


class FakeResp:
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False
    def read(self):
        return json.dumps(fake).encode()


urllib.request.urlopen = lambda url, timeout=8: FakeResp()
cap = ti.poll_and_capture()
chk("1 seule capture (commande valide du chat de Sam)", len(calls) == 1, str(calls))
chk("bons paramètres capturés", calls and calls[0][:3] == ("GOLD", "SHORT", 4150.0))
chk("ts = heure réelle du message", calls and calls[0][4] is not None)
chk("message d'un AUTRE chat ignoré (sécurité)", all(c[:3] != ("GOLD", "LONG", 1.0) for c in calls))
chk("confirmation envoyée", any("capturé" in s for s in sent))
chk("offset avancé (pas de retraitement)", json.load(open(ti.STATE)).get("offset") == 12)
os.remove(ti.STATE) if os.path.exists(ti.STATE) else None

print()
if FAIL:
    print(f"X ÉCHEC(S): {FAIL}")
    raise SystemExit(1)
print("OK, telegram_inbox : parsing + capture + sécurité chat validés.")
