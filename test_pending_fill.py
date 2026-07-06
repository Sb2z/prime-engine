#!/usr/bin/env python3
"""TEST fill-tracking des A_SETUP (journal PENDING→OPEN/EXPIRED) — exigé avant
commit (audit 2026-06-17). Isolé sur un journal temporaire."""
import datetime
import tempfile

import journal

journal.JOURNAL_FILE = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
journal.save_journal({"signals": [], "stats": {}})

FAIL = []


def chk(n, ok, d=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {n}" + (f" — {d}" if d else ""))
    if not ok:
        FAIL.append(n)


now = datetime.datetime.now(datetime.timezone.utc)
ts0 = now.timestamp()

print("1. log_pending_setup crée un PENDING")
jid = journal.log_pending_setup("GOLD", "LONG", 100.0, 98.0, 104.0, valid_minutes=45, rr=2.5)
sig = next(s for s in journal.load_journal()["signals"] if s["id"] == jid)
chk("status PENDING", sig["status"] == "PENDING")
chk("entry/stop/tp persistés", sig["entry"] == 100 and sig["stop"] == 98 and sig["tp1"] == 104)
chk("rr journalisé (observabilité capture)", sig.get("rr") == 2.5, str(sig.get("rr")))

print("2. anti-doublon : re-log identique ignoré")
jid2 = journal.log_pending_setup("GOLD", "LONG", 100.0, 98.0, 104.0)
chk("2e log ignoré (None)", jid2 is None)
chk("toujours 1 signal", len(journal.load_journal()["signals"]) == 1)

print("3. remplissage : le bas d'une bougie touche l'entrée -> OPEN")
candles = {"GOLD": [[ts0 + 60, 101.0, 101.5, 99.9, 101.0, 0]]}  # low 99.9 <= entry 100
journal.evaluate_open({"GOLD": {"lp": 101.0}}, candles_1m=candles)
sig = next(s for s in journal.load_journal()["signals"] if s["id"] == jid)
chk("PENDING -> OPEN", sig["status"] == "OPEN", sig["status"])
chk("filled_ts posé", bool(sig.get("filled_ts")))

print("4. SHORT non rempli + délai dépassé -> EXPIRED (NOFILL)")
j = journal.load_journal()
j["signals"].append({
    "id": "AI_GOLD_exp", "status": "PENDING", "asset": "GOLD", "direction": "SHORT",
    "entry": 200.0, "stop": 204.0, "tp1": 192.0, "trader": "AI",
    "ts": (now - datetime.timedelta(minutes=60)).isoformat(),
    "trigger_ts": (now - datetime.timedelta(minutes=60)).isoformat(),
    "entry_deadline": (now - datetime.timedelta(minutes=30)).isoformat(),
    "hi_since": 200.0, "lo_since": 200.0, "filled_ts": None, "session": "AI",
})
journal.save_journal(j)
# SHORT entry 200 : remplit si un HAUT >= 200 ; ici le prix reste vers 190 (jamais touché)
candles2 = {"GOLD": [[ts0 - 2400, 190.0, 191.0, 189.0, 190.0, 0]]}
journal.evaluate_open({"GOLD": {"lp": 190.0}}, candles_1m=candles2)
sig2 = next(s for s in journal.load_journal()["signals"] if s["id"] == "AI_GOLD_exp")
chk("PENDING -> EXPIRED", sig2["status"] == "EXPIRED", sig2["status"])
chk("result NOFILL", sig2.get("result") == "NOFILL")

print("5. stats : taux de remplissage exposé")
st = journal.load_journal()["stats"]
chk("ai_fill_rate présent", "ai_fill_rate" in st)
chk("ai_expired_nofill >= 1", st.get("ai_expired_nofill", 0) >= 1)
chk("fill_rate cohérent (1 rempli / 1 expiré = 50%)", st.get("ai_fill_rate") == 50.0, str(st.get("ai_fill_rate")))

print("6. SL sur la bougie de FILL : mèche touche entrée ET stop -> CLOSED LOSS (fix audit 06-18)")
journal.save_journal({"signals": [], "stats": {}})
jid_sl = journal.log_pending_setup("GOLD", "LONG", 100.0, 99.0, 104.0, valid_minutes=45)
# bougie de fill : low 98.5 remplit l'entrée 100 ET casse le stop 99 dans la même minute
candles_sl = {"GOLD": [[ts0 + 60, 100.2, 100.3, 98.5, 99.5, 0]]}
journal.evaluate_open({"GOLD": {"lp": 99.5}}, candles_1m=candles_sl)
sig_sl = next(s for s in journal.load_journal()["signals"] if s["id"] == jid_sl)
chk("fill+SL même bougie -> CLOSED (stop-run de la bougie de fill capté)", sig_sl["status"] == "CLOSED", sig_sl["status"])
chk("result LOSS", sig_sl.get("result") == "LOSS", str(sig_sl.get("result")))

print("7. fill SANS breach du stop -> reste OPEN (pas de faux LOSS)")
journal.save_journal({"signals": [], "stats": {}})
jid_ok = journal.log_pending_setup("GOLD", "LONG", 100.0, 98.0, 104.0, valid_minutes=45)
candles_ok = {"GOLD": [[ts0 + 60, 100.1, 101.0, 99.9, 100.5, 0]]}  # low 99.9 > stop 98
journal.evaluate_open({"GOLD": {"lp": 100.5}}, candles_1m=candles_ok)
sig_ok = next(s for s in journal.load_journal()["signals"] if s["id"] == jid_ok)
chk("fill propre -> OPEN", sig_ok["status"] == "OPEN", sig_ok["status"])

print("8. CROSS-SOURCE : bougie d'une autre source que l'entrée -> PAS de fill (anti-basis, bug #1)")
journal.save_journal({"signals": [], "stats": {}})
jid_x = journal.log_pending_setup("GOLD", "LONG", 100.0, 98.0, 104.0, valid_minutes=45, price_source="tradingview")
sigx = next(s for s in journal.load_journal()["signals"] if s["id"] == jid_x)
chk("price_source stocké dans le PENDING", sigx.get("price_source") == "tradingview")
# bougie qui REMPLIRAIT l'entrée (low 99.9 <= 100) MAIS source yfinance != tradingview
cx = {"GOLD": [[ts0 + 60, 101.0, 101.5, 99.9, 101.0, 0]]}
journal.evaluate_open({"GOLD": {"lp": 101.0}}, candles_1m=cx, candle_sources={"GOLD": "yfinance"})
sigx = next(s for s in journal.load_journal()["signals"] if s["id"] == jid_x)
chk("cross-source -> reste PENDING (pas de faux fill)", sigx["status"] == "PENDING", sigx["status"])
chk("fill_quality = CROSS_SOURCE", sigx.get("fill_quality") == "CROSS_SOURCE", str(sigx.get("fill_quality")))

print("9. MÊME source (tradingview) -> fill normal")
cx2 = {"GOLD": [[ts0 + 120, 101.0, 101.5, 99.9, 101.0, 0]]}
journal.evaluate_open({"GOLD": {"lp": 101.0}}, candles_1m=cx2, candle_sources={"GOLD": "tradingview+cache"})
sigx = next(s for s in journal.load_journal()["signals"] if s["id"] == jid_x)
chk("même fournisseur (tradingview, +cache ignoré) -> OPEN", sigx["status"] == "OPEN", sigx["status"])

print("10. CROSS-SOURCE sur un OPEN -> pas d'exit sur la mauvaise référence")
journal.save_journal({"signals": [], "stats": {}})
jid_o = journal.log_pending_setup("GOLD", "LONG", 100.0, 98.0, 104.0, valid_minutes=45, price_source="tradingview")
journal.evaluate_open({"GOLD": {"lp": 100.5}}, candles_1m={"GOLD": [[ts0 + 60, 100.1, 101.0, 99.9, 100.5, 0]]}, candle_sources={"GOLD": "tradingview"})
# bougie yfinance qui casserait le stop (low 97 <= 98) -> NE doit PAS sortir
journal.evaluate_open({"GOLD": {"lp": 97.5}}, candles_1m={"GOLD": [[ts0 + 180, 98.0, 98.5, 97.0, 97.5, 0]]}, candle_sources={"GOLD": "yfinance"})
sigo = next(s for s in journal.load_journal()["signals"] if s["id"] == jid_o)
chk("OPEN cross-source -> reste OPEN (pas de faux SL)", sigo["status"] == "OPEN", sigo["status"])
chk("OPEN cross-source -> fill_quality CROSS_SOURCE", sigo.get("fill_quality") == "CROSS_SOURCE", str(sigo.get("fill_quality")))

print()
if FAIL:
    print(f"X {len(FAIL)} ÉCHEC(S): {FAIL}")
    raise SystemExit(1)
print("OK — fill-tracking PENDING→OPEN/EXPIRED validé.")
