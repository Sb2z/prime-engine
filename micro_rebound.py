#!/usr/bin/env python3
"""
MICRO-REBOUND, Scalp des micro-rebonds entre order blocks (stratégie gagnante de Sam)
══════════════════════════════════════════════════════════════════
Setup validé en réel (+30% en 1 jour) :
  Le prix tape une résistance/OB et MET DU TEMPS à casser le prochain order block
  → un micro-rebond se forme → on entre dessus → SORTIE RAPIDE (petite TF).

Principe : TOUJOURS conscient de la tendance (biais), MAIS scalper aussi les
micro-rebonds (oscillations) qui sont ultra-rentables. Exit rapide, stop serré.
Ces scalps ont un RR plus faible (1:1 à 1:1.5) compensé par un WIN RATE élevé.
"""

import smc


def _atr(candles, period=14):
    if len(candles) < period + 1:
        return None
    trs = []
    for i in range(1, len(candles)):
        h, l = float(candles[i][2]), float(candles[i][3])
        pc = float(candles[i - 1][4])
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return sum(trs[-period:]) / period


def _is_stalling(candles, lookback=6, max_range_atr=1.8):
    """Le prix consolide (met du temps à casser) = pré-condition du micro-rebond."""
    atr = _atr(candles)
    if not atr:
        return False
    seg = candles[-lookback:]
    hi = max(float(c[2]) for c in seg)
    lo = min(float(c[3]) for c in seg)
    return (hi - lo) <= max_range_atr * atr   # range serré = consolidation


def _rejection(candle, side):
    """Détecte une mèche de rejet (pinbar) sur une bougie."""
    o, h, l, c = float(candle[1]), float(candle[2]), float(candle[3]), float(candle[4])
    body = abs(c - o) or 0.01
    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l
    if side == "low" and lower_wick > body * 1.2:   # rejet par le bas = rebond haussier
        return True
    if side == "high" and upper_wick > body * 1.2:  # rejet par le haut = rebond baissier
        return True
    return False


def detect_micro_rebound(candles_5m, trend="RANGE"):
    """
    Détecte un micro-rebond scalpable entre order blocks.
    Retourne un setup {direction, entry, stop, tp_fast, rr, note} ou None.
    """
    if not candles_5m or len(candles_5m) < 20:
        return None
    price = float(candles_5m[-1][4])
    atr = _atr(candles_5m)
    if not atr:
        return None
    obs = smc.find_order_blocks(candles_5m, lookback=40)
    smc_res = smc.smc_analysis(candles_5m)
    stalling = _is_stalling(candles_5m)
    last = candles_5m[-1]

    # Order blocks au-dessus / en-dessous du prix
    ob_above = sorted([o for o in obs if o["low"] > price], key=lambda x: x["low"])
    ob_below = sorted([o for o in obs if o["high"] < price], key=lambda x: -x["high"])

    setups = []

    # ── Micro-rebond HAUSSIER : prix tape un OB/support en-dessous + rejet par le bas ──
    near_support = ob_below and abs(price - ob_below[0]["high"]) < 0.6 * atr
    if (near_support or smc_res.get("structure") == "UPTREND") and _rejection(last, "low") and stalling:
        target = ob_above[0]["low"] if ob_above else round(price + 1.2 * atr, 2)
        entry = price
        stop = round(price - 0.7 * atr, 2)
        rr = round((target - entry) / (entry - stop), 2) if entry > stop else 0
        setups.append({"direction": "LONG", "entry": round(entry, 2), "stop": stop,
                       "tp_fast": round(target, 2), "rr": rr,
                       "note": "Micro-rebond haussier : rejet du support + consolidation → scalp vers l'OB au-dessus"})

    # ── Micro-rebond BAISSIER : prix tape une résistance/OB au-dessus + rejet par le haut ──
    near_resistance = ob_above and abs(price - ob_above[0]["low"]) < 0.6 * atr
    if (near_resistance or smc_res.get("structure") == "DOWNTREND") and _rejection(last, "high") and stalling:
        target = ob_below[0]["high"] if ob_below else round(price - 1.2 * atr, 2)
        entry = price
        stop = round(price + 0.7 * atr, 2)
        rr = round((entry - target) / (stop - entry), 2) if stop > entry else 0
        setups.append({"direction": "SHORT", "entry": round(entry, 2), "stop": stop,
                       "tp_fast": round(target, 2), "rr": rr,
                       "note": "Micro-rebond baissier : rejet de la résistance + consolidation → scalp vers l'OB en-dessous"})

    if not setups:
        return {"setup": None, "stalling": stalling, "structure": smc_res.get("structure"),
                "atr_5m": round(atr, 2),
                "note": "Pas de micro-rebond actionnable (pas de rejet/stall à un OB)"}

    # Priorité au scalp ALIGNÉ avec la tendance (mais les 2 sont jouables, Sam scalpe les deux)
    setups.sort(key=lambda s: (s["direction"] == "LONG") == (trend == "UPTREND"), reverse=True)
    best = setups[0]
    best["aligned_with_trend"] = (best["direction"] == "LONG") == (trend == "UPTREND")
    return {"setup": best, "all": setups, "stalling": stalling,
            "structure": smc_res.get("structure"), "atr_5m": round(atr, 2)}


if __name__ == "__main__":
    from tv_candles import TVCandleClient
    cl = TVCandleClient(symbols=["GOLD"], timeframe="5m", n_bars=80, timeout=25)
    cl.fetch_ta()
    candles = cl._candles.get("GOLD", [])
    r = detect_micro_rebound(candles, trend="DOWNTREND")
    print("\n⚡ MICRO-REBOUND GOLD 5m\n")
    if r and r.get("setup"):
        s = r["setup"]
        print(f"  {s['direction']} @ {s['entry']} | Stop {s['stop']} | TP rapide {s['tp_fast']} | RR {s['rr']}")
        print(f"  Aligné tendance: {s.get('aligned_with_trend')} | {s['note']}")
    else:
        print(f"  {r.get('note') if r else 'pas de données'}")
        print(f"  (stalling={r.get('stalling')}, structure={r.get('structure')}, ATR 5m={r.get('atr_5m')})")
