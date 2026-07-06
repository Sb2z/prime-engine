#!/usr/bin/env python3
"""TEST capture contexte trade (anti-lookahead). Parquet SYNTHÉTIQUE + jsonl temp,
aucune donnée live touchée. Prouve : contexte = ligne <= ts (jamais future), aucune
colonne d'outcome dans le contexte, outcome backfillé uniquement depuis prix POSTÉRIEURS."""
import datetime as dt
import json
import os
import tempfile
import duckdb
import user_trade_context as utc

FAIL = []


def chk(n, ok, d=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {n}" + (f" — {d}" if d else ""))
    if not ok:
        FAIL.append(n)


tmp = tempfile.gettempdir()
PARQUET = os.path.join(tmp, "_utc_feat.parquet").replace("\\", "/")
OUTJL = os.path.join(tmp, "_utc_out.jsonl")
for f in (OUTJL,):
    if os.path.exists(f):
        os.remove(f)

# Parquet synthétique : GOLD toutes les 5 min, prix qui baisse, + colonnes d'OUTCOME
# (ret_*) qui NE doivent JAMAIS finir dans le contexte capturé.
con = duckdb.connect()
con.execute(f"""
COPY (SELECT * FROM (VALUES
  (TIMESTAMPTZ '2026-06-19 10:00:00+00','GOLD',4000.0,'WATCH',7.0,50.0,0.9,0.9,0.9,'OK'),
  (TIMESTAMPTZ '2026-06-19 10:05:00+00','GOLD',3995.0,'A_SETUP',8.0,-120.0,0.9,0.9,0.9,'OK'),
  (TIMESTAMPTZ '2026-06-19 10:10:00+00','GOLD',3990.0,'WATCH',6.0,-80.0,0.9,0.9,0.9,'OK'),
  (TIMESTAMPTZ '2026-06-19 11:07:00+00','GOLD',3960.0,'WATCH',6.0,-30.0,NULL,NULL,NULL,'OK')
) AS t(ts,asset,price,grade,conf,of_delta,ret_15m,ret_1h,ret_4h,outcome_quality))
TO '{PARQUET}' (FORMAT PARQUET)""")

print("Capture ANTI-LOOKAHEAD")
trade_ts = dt.datetime(2026, 6, 19, 10, 7, 0, tzinfo=dt.timezone.utc)  # entre 10:05 et 10:10
rec = utc.capture("GOLD", "SHORT", 3994.0, ts=trade_ts, parquet=PARQUET, out=OUTJL)
ctx = rec["context"]
chk("contexte capturé", ctx is not None)
ctx_utc = dt.datetime.fromisoformat(str(ctx.get("ts")).replace(" ", "T", 1)).astimezone(dt.timezone.utc)
chk("contexte = instant 10:05 UTC (<= ts ; PAS 10:10 future)", ctx_utc == dt.datetime(2026, 6, 19, 10, 5, tzinfo=dt.timezone.utc), str(ctx_utc))
chk("grade du bon cycle (A_SETUP @10:05)", ctx.get("grade") == "A_SETUP", str(ctx.get("grade")))
chk("AUCUNE colonne d'outcome dans le contexte (anti-lookahead)",
    not any(k in ctx for k in ("ret_15m", "ret_1h", "ret_4h", "outcome_quality")), str([k for k in ctx if k.startswith("ret") or "outcome" in k]))
chk("outcome=None au moment du log", rec["outcome"] is None)
chk("heure réelle du trade stockée", rec["ts"].startswith("2026-06-19T10:07"))
chk("âge du contexte ~2 min", rec["context_age_min"] == 2.0, str(rec["context_age_min"]))

print("Backfill OUTCOME (prix POSTÉRIEURS au ts uniquement)")
# now = 10:07 + >1h -> ret_1h calculable depuis le prix à 11:07 (3960)
n = utc.backfill_outcomes(parquet=PARQUET, out=OUTJL, now=dt.datetime(2026, 6, 19, 14, 0, 0, tzinfo=dt.timezone.utc))
rec2 = [json.loads(l) for l in open(OUTJL, encoding="utf-8")][0]
oc = rec2.get("outcome") or {}
chk("outcome backfillé", n == 1 and bool(oc), str(oc))
# SHORT, entry 3994, prix 1h après (11:07) = 3960 -> ret_1h = +(3994-3960)/3994*100 ≈ +0.85%
chk("ret_1h SHORT correct (prix a baissé -> gain)", oc.get("ret_1h") and oc["ret_1h"] > 0, str(oc.get("ret_1h")))

print("Summary + garde-fou modèle")
s = utc.summary(out=OUTJL)
chk("summary cohérent", s["captured"] == 1 and s["avec_contexte"] == 1 and s["avec_outcome"] == 1)
chk("pret_pour_modele=False (1 jour < 15)", s["pret_pour_modele"] is False)

os.remove(OUTJL) if os.path.exists(OUTJL) else None
print()
if FAIL:
    print(f"X ÉCHEC(S): {FAIL}")
    raise SystemExit(1)
print("OK — capture contexte trade anti-lookahead + backfill outcome validés.")
