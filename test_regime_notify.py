#!/usr/bin/env python3
"""TEST mineurs 2026-06-18 :
  - regime.detect : trou ADX 22-25 fermé (trend propre à ADX modéré n'est plus
    classé TRANSITION).
  - notify : compteur d'échecs Telegram consécutifs (+ reprise).
Pur : aucun réseau, aucune base. notify.STATE/_log_outbox redirigés en temp."""
import os
import tempfile
import regime
import notify

FAIL = []


def chk(n, ok, d=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {n}" + (f", {d}" if d else ""))
    if not ok:
        FAIL.append(n)


def candles(closes):
    return [[i, c, c + 0.5, c - 0.5, c, 1000.0] for i, c in enumerate(closes)]


print("regime, trou ADX 22-25 fermé")
up = candles([100 + i * 0.5 for i in range(40)])        # monotone -> ER ~1.0 (>=0.45)
chop = candles([100 + (i % 2) for i in range(40)])      # alterné -> ER ~0.03 (<=0.30)
r_mod = regime.detect(up, adx=23)
chk("ADX 23 + trend propre (ER>=0.45) -> TENDANCE MOYENNE (était TRANSITION)",
    "MOYENNE" in r_mod["regime"], f"{r_mod['regime']} er={r_mod['er']}")
r_strong = regime.detect(up, adx=27)
chk("ADX 27 + ER>=0.45 -> TENDANCE PROPRE (inchangé)", "PROPRE" in r_strong["regime"], r_strong["regime"])
r_chop = regime.detect(chop, adx=23)
chk("ADX 23 + choppy (ER<=0.30) -> TRANSITION", "TRANSITION" in r_chop["regime"], r_chop["regime"])
r_range = regime.detect(up, adx=15)
chk("ADX 15 -> RANGE", "RANGE" in r_range["regime"], r_range["regime"])

print("notify, compteur d'échecs Telegram consécutifs")
notify.STATE = os.path.join(tempfile.gettempdir(), "test_tgstate.json")
if os.path.exists(notify.STATE):
    os.remove(notify.STATE)
logs = []
notify._log_outbox = lambda text, silent, ok: logs.append(text)
chk("compteur initial = 0", notify.consecutive_failures() == 0)
notify._bump_failures(False, True)
notify._bump_failures(False, True)
chk("2 échecs (API joignable) -> compteur 2", notify.consecutive_failures() == 2, str(notify.consecutive_failures()))
notify._bump_failures(False, False)
chk("credentials manquants n'incrémente PAS", notify.consecutive_failures() == 2, str(notify.consecutive_failures()))
notify._bump_failures(True, True)
chk("reprise -> compteur remis à 0", notify.consecutive_failures() == 0)
chk("note de reprise loggée dans l'outbox", any("rétabli" in l for l in logs), str(logs))
os.remove(notify.STATE) if os.path.exists(notify.STATE) else None

print()
if FAIL:
    print(f"X ÉCHEC(S): {FAIL}")
    raise SystemExit(1)
print("OK, fix régime ADX 22-25 + compteur Telegram validés.")
