#!/usr/bin/env python3
"""
PAPER LAB — validation forward AUTOMATIQUE des hypothèses du mining (2026-07-02).
═══════════════════════════════════════════════════════════════════════════════
Le mining multi-agents a produit 2 hypothèses fortes mais NON prouvées (t-stats
sous le seuil après déflation, fenêtres courtes). Notre règle : on ne trade RIEN
en réel sans validation forward. Ce module journalise donc chaque signal EN PAPIER,
tout seul, chaque cycle du watcher — dans 15-20 jours on aura le verdict.

  H1 « gold_ny_fade » : à 16h30 Paris, prendre l'INVERSE du mouvement GOLD
     15h30->16h30 ; sorties mesurées à 17h30 ET 20h00. (mesuré : +0,21 à +0,49%/
     trade, t=2,8-3,3 AVANT déflation, 16 jours — réversion d'ouverture NY + fixing Londres.)
  H2 « us500_value_reversion » : LONG US500 quand of_imbalance < 0.12 (prix sous
     la Value Area) en heures US (15h30-22h Paris) ; sorties 1h et 4h.
     (mesuré : +0,10%/trade net @1h, 7 jours, 18 trades.)

ANTI-LOOKAHEAD : ne lit que feature_exports/features.parquet (lignes <= maintenant),
jamais prime.duckdb. État/trades dans SES fichiers (aucune écriture partagée).
Appelé par prime_watcher à chaque cycle (~5 min) via tick() — jamais bloquant.
CLI :  python paper_lab.py          -> tick manuel
       python paper_lab.py summary  -> verdict par stratégie (net des coûts)
"""
import datetime as dt
import json
import os
from zoneinfo import ZoneInfo

PARIS = ZoneInfo("Europe/Paris")
PQ = "/Users/sam/trading/feature_exports/features.parquet"
OUT = "/Users/sam/trading/paper_trades.jsonl"
# coût aller-retour (spread session, cf. costs.py / mining 02-07) en %
RT_COST = {"GOLD": 0.024, "US500": 0.040}
STRAT_COST = {"gold_imb_fade": 0.030}   # H3 tient l'état jusqu'à 22h -> spread off inclus
IMB_LONG_MAX = 0.12          # H2 : prix sous la Value Area
IMB_FADE_TH = 1.0            # H3 : état « étiré » au-delà de la Value Area


def _con():
    import duckdb
    return duckdb.connect()


def _px_at(con, asset, ts_iso, after=False, tol_min=12):
    """Prix du parquet le plus proche <= ts (ou >= si after). None si trop loin."""
    op, order = ("<=", "DESC") if not after else (">=", "ASC")
    r = con.execute(
        f"SELECT ts, price FROM read_parquet('{PQ}') WHERE asset=? AND ts {op} ? "
        f"ORDER BY ts {order} LIMIT 1", [asset, ts_iso]).fetchone()
    if not r or r[1] is None:
        return None
    got = dt.datetime.fromisoformat(str(r[0]))
    want = dt.datetime.fromisoformat(ts_iso)
    if abs((got - want).total_seconds()) > tol_min * 60:
        return None
    return float(r[1])


def _load():
    if not os.path.exists(OUT):
        return []
    return [json.loads(l) for l in open(OUT, encoding="utf-8") if l.strip()]


def _append(rec):
    with open(OUT, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _rewrite(recs):
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
        f.flush(); os.fsync(f.fileno())
    os.replace(tmp, OUT)


def _h1_gold_ny_fade(con, now_p, recs):
    """Signal 1x/jour ouvré, fenêtre 16h30-17h00 Paris."""
    if now_p.weekday() >= 5 or not (
            (now_p.hour == 16 and now_p.minute >= 30) or (now_p.hour == 17 and now_p.minute == 0)):
        return None
    day = now_p.date().isoformat()
    if any(r["strategy"] == "gold_ny_fade" and r["day"] == day for r in recs):
        return None
    t1530 = now_p.replace(hour=15, minute=30, second=0, microsecond=0)
    t1630 = now_p.replace(hour=16, minute=30, second=0, microsecond=0)
    p1, p2 = _px_at(con, "GOLD", t1530.isoformat()), _px_at(con, "GOLD", t1630.isoformat())
    if p1 is None or p2 is None or p1 == p2:
        return None
    direction = "SHORT" if p2 > p1 else "LONG"   # fade du mouvement 1ère heure NY
    return {
        "id": f"H1_{day}", "strategy": "gold_ny_fade", "asset": "GOLD", "day": day,
        "direction": direction, "entry_ts": t1630.isoformat(), "entry_px": p2,
        "move_1h_pct": round((p2 - p1) / p1 * 100, 4),
        "exits": {"17h30": None, "20h00": None},
        "exit_ts": {"17h30": now_p.replace(hour=17, minute=30, second=0, microsecond=0).isoformat(),
                    "20h00": now_p.replace(hour=20, minute=0, second=0, microsecond=0).isoformat()},
    }


def _h2_us500_value_reversion(con, now_p, recs):
    """LONG US500 sous la Value Area, heures US, 1 position à la fois."""
    if now_p.weekday() >= 5 or not (15 <= now_p.hour <= 21):
        return None
    if now_p.hour == 15 and now_p.minute < 30:
        return None
    # une seule position ouverte à la fois (dé-chevauché comme dans le mining)
    for r in recs:
        if r["strategy"] == "us500_value_reversion" and r["exits"].get("4h") is None:
            horizon = dt.datetime.fromisoformat(r["exit_ts"]["4h"])
            if now_p < horizon:
                return None
    row = con.execute(
        f"SELECT ts, price, of_imbalance FROM read_parquet('{PQ}') WHERE asset='US500' "
        f"ORDER BY ts DESC LIMIT 1").fetchone()
    if not row or row[1] is None or row[2] is None:
        return None
    ts = dt.datetime.fromisoformat(str(row[0]))
    if (now_p - ts).total_seconds() > 12 * 60 or float(row[2]) >= IMB_LONG_MAX:
        return None
    return {
        "id": f"H2_{int(now_p.timestamp())}", "strategy": "us500_value_reversion",
        "asset": "US500", "day": now_p.date().isoformat(), "direction": "LONG",
        "entry_ts": ts.isoformat(), "entry_px": float(row[1]),
        "of_imbalance": round(float(row[2]), 4),
        "exits": {"1h": None, "4h": None},
        "exit_ts": {"1h": (ts + dt.timedelta(hours=1)).isoformat(),
                    "4h": (ts + dt.timedelta(hours=4)).isoformat()},
    }


def _h3_gold_imb_fade(con, now_p, recs):
    """H3 (mining 02-07, règle FIGÉE avant les données) : fade de l'ÉTAT étiré
    GOLD — SHORT si of_imbalance>+1, LONG si <-1 ; sortie quand |imb|<1 ou 22h
    Paris ; flat overnight ; 1 position à la fois. Gère AUSSI sa clôture.
    (mesuré : +0,15%/j brut, 6/11 jours seulement -> paper obligatoire.)"""
    if now_p.weekday() >= 5:
        return None
    row = con.execute(
        f"SELECT ts, price, of_imbalance FROM read_parquet('{PQ}') WHERE asset='GOLD' "
        f"ORDER BY ts DESC LIMIT 1").fetchone()
    if not row or row[1] is None or row[2] is None:
        return None
    ts = dt.datetime.fromisoformat(str(row[0]))
    if (now_p - ts).total_seconds() > 12 * 60:
        return None
    px, imb = float(row[1]), float(row[2])
    open_pos = next((r for r in recs if r["strategy"] == "gold_imb_fade"
                     and r["exits"].get("close") is None), None)
    if open_pos:
        if abs(imb) < IMB_FADE_TH or now_p.hour >= 22:
            sign = 1 if open_pos["direction"] == "LONG" else -1
            open_pos["exits"]["close"] = round(
                sign * (px - open_pos["entry_px"]) / open_pos["entry_px"] * 100, 4)
            open_pos["exit_ts"]["close"] = ts.isoformat()
            _rewrite(recs)
        return None
    if now_p.hour >= 21 or now_p.hour < 1 or abs(imb) <= IMB_FADE_TH:
        return None
    return {
        "id": f"H3_{int(now_p.timestamp())}", "strategy": "gold_imb_fade",
        "asset": "GOLD", "day": now_p.date().isoformat(),
        "direction": "SHORT" if imb > 0 else "LONG",
        "entry_ts": ts.isoformat(), "entry_px": px, "of_imbalance": round(imb, 4),
        "exits": {"close": None}, "exit_ts": {"close": None},
    }


def _backfill(con, now_p, recs):
    """Renseigne les sorties dont l'horizon est passé (prix >= horizon, anti-lookahead)."""
    n = 0
    for r in recs:
        sign = 1 if r["direction"] == "LONG" else -1
        for k, ts_iso in r["exit_ts"].items():
            if r["exits"].get(k) is not None or ts_iso is None:
                continue  # ts None = sortie dynamique (H3), gérée par sa stratégie
            t_exit = dt.datetime.fromisoformat(ts_iso)
            if now_p < t_exit:
                continue
            px = _px_at(con, r["asset"], ts_iso, after=True)
            if px is not None:
                r["exits"][k] = round(sign * (px - r["entry_px"]) / r["entry_px"] * 100, 4)
                n += 1
    return n


def tick():
    """Un passage : nouveaux signaux + backfill. Jamais d'exception propagée."""
    try:
        now_p = dt.datetime.now(PARIS)
        recs = _load()
        con = _con()
        opened = []
        for fn in (_h1_gold_ny_fade, _h2_us500_value_reversion, _h3_gold_imb_fade):
            rec = fn(con, now_p, recs)
            if rec:
                _append(rec); recs.append(rec); opened.append(rec["id"])
        if _backfill(con, now_p, recs):
            _rewrite(recs)
        return opened
    except Exception:
        return []


def summary():
    recs = _load()
    out = {}
    for strat in ("gold_ny_fade", "us500_value_reversion", "gold_imb_fade"):
        rs = [r for r in recs if r["strategy"] == strat]
        line = {"signaux": len(rs), "jours": len({r["day"] for r in rs})}
        for k in (rs[0]["exits"].keys() if rs else []):
            done = [r["exits"][k] for r in rs if r["exits"].get(k) is not None]
            if done:
                cost = STRAT_COST.get(strat, RT_COST.get(rs[0]["asset"], 0.04))
                net = [v - cost for v in done]
                line[f"sortie_{k}"] = {
                    "n": len(net), "wr": round(sum(1 for v in net if v > 0) / len(net) * 100),
                    "net_moy_pct": round(sum(net) / len(net), 4),
                }
        out[strat] = line
    return out


if __name__ == "__main__":
    import sys
    if sys.argv[1:] and sys.argv[1] == "summary":
        print(json.dumps(summary(), indent=1, ensure_ascii=False))
    else:
        print("ouverts:", tick())
