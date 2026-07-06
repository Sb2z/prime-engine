#!/usr/bin/env python3
"""
SENTINEL-500, Edge intraday : VWAP + Opening Range
══════════════════════════════════════════════════════════════════
VWAP de session (ancré à l'ouverture cash US 15:30 Paris / 13:30 UTC) :
  le prix de référence des institutions. Au-dessus = biais haussier intraday.
Opening Range (30 premières min) : cassure = direction de la séance.
Score positif = bullish, négatif = bearish.
"""

import datetime
from tv_candles import TVCandleClient

CASH_OPEN_UTC_H, CASH_OPEN_UTC_M = 13, 30   # 15:30 Paris


def _session_open_ts():
    now = datetime.datetime.now(datetime.timezone.utc)
    op = now.replace(hour=CASH_OPEN_UTC_H, minute=CASH_OPEN_UTC_M, second=0, microsecond=0)
    if now < op:                      # avant l'ouverture → session précédente
        op -= datetime.timedelta(days=1)
    # recule sur le dernier jour de semaine
    while op.weekday() >= 5:
        op -= datetime.timedelta(days=1)
    return op.timestamp()


def analyze_vwap_or(timeframe="5m"):
    cl = TVCandleClient(symbols=["US500"], timeframe=timeframe, n_bars=150, timeout=24)
    cl.fetch_ta()
    candles = cl._candles.get("US500", [])
    if len(candles) < 10:
        return {"error": "pas assez de bougies"}

    sess_ts = _session_open_ts()
    sess = [c for c in candles if c[0] >= sess_ts]
    if len(sess) < 3:
        sess = candles[-30:]          # fallback : 30 dernières bougies

    # VWAP (fallback moyenne typique si pas de volume)
    cum_pv = cum_v = 0.0
    tps = []
    for c in sess:
        o, h, l, cl_ = float(c[1]), float(c[2]), float(c[3]), float(c[4])
        v = float(c[5]) if len(c) > 5 and c[5] else 0.0
        tp = (h + l + cl_) / 3
        tps.append(tp)
        cum_pv += tp * v
        cum_v += v
    vwap = (cum_pv / cum_v) if cum_v > 0 else (sum(tps) / len(tps))

    # Écart-type pour bandes VWAP
    mean_tp = sum(tps) / len(tps)
    var = sum((x - mean_tp) ** 2 for x in tps) / len(tps)
    sd = var ** 0.5

    # Opening Range = 6 premières bougies 5m (30 min)
    or_bars = sess[:6] if len(sess) >= 6 else sess
    or_high = max(float(c[2]) for c in or_bars)
    or_low = min(float(c[3]) for c in or_bars)

    price = float(sess[-1][4])

    # Position vs VWAP
    signals, score = [], 0.0
    dist_vwap = (price - vwap) / vwap * 100
    if price > vwap:
        score += 0.6
        signals.append(f"🟢 Prix > VWAP ({vwap:.1f}) de {dist_vwap:+.2f}% → biais acheteur intraday")
    else:
        score -= 0.6
        signals.append(f"🔴 Prix < VWAP ({vwap:.1f}) de {dist_vwap:+.2f}% → biais vendeur intraday")

    # Position vs Opening Range
    if price > or_high:
        score += 0.5
        signals.append(f"🟢 Cassure HAUTE de l'Opening Range ({or_high:.1f}) → momentum acheteur")
        or_state = "BREAKOUT_UP"
    elif price < or_low:
        score -= 0.5
        signals.append(f"🔴 Cassure BASSE de l'Opening Range ({or_low:.1f}) → momentum vendeur")
        or_state = "BREAKOUT_DOWN"
    else:
        signals.append(f"⚪ Dans l'Opening Range ({or_low:.1f}-{or_high:.1f}) → indécision, attendre la cassure")
        or_state = "INSIDE"

    # Extension (loin du VWAP = risque de retour à la moyenne)
    if abs(dist_vwap) > 0.6:
        signals.append(f"⚠️ Prix étendu à {dist_vwap:+.2f}% du VWAP → risque de retour à la moyenne")

    return {
        "vwap": round(vwap, 1), "vwap_upper": round(vwap + sd, 1), "vwap_lower": round(vwap - sd, 1),
        "or_high": round(or_high, 1), "or_low": round(or_low, 1), "or_state": or_state,
        "price": round(price, 1), "dist_vwap_pct": round(dist_vwap, 2),
        "score": round(score, 2), "signals": signals, "n_bars": len(sess),
    }


if __name__ == "__main__":
    r = analyze_vwap_or()
    if "error" in r:
        print("⚠️", r["error"])
    else:
        print(f"\n📊 VWAP/OR S&P, score {r['score']:+.2f}  ({r['n_bars']} bougies session)\n")
        print(f"  VWAP {r['vwap']} (bandes {r['vwap_lower']}-{r['vwap_upper']})")
        print(f"  Opening Range {r['or_low']}-{r['or_high']} → {r['or_state']}")
        print(f"  Prix {r['price']} ({r['dist_vwap_pct']:+.2f}% vs VWAP)\n")
        for s in r["signals"]:
            print(f"   {s}")
