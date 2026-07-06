#!/usr/bin/env python3
"""
SMC — Smart Money Concepts (détection sur bougies réelles)
══════════════════════════════════════════════════════════════════
Le cœur des méthodes Raja Banks / ICT :
  • Structure de marché (HH/HL uptrend, LH/LL downtrend)
  • BOS (Break of Structure) / CHoCH (Change of Character = reversal)
  • Order Blocks (zone institutionnelle = dernière bougie opposée avant impulsion)
  • Fair Value Gaps / Imbalances (3 bougies, déséquilibre à combler)
  • Liquidité (equal highs/lows = pools de stops ciblés)
Retourne un biais SMC + signaux + score (pour confluence ET pour mesurer le win rate).
"""


def _swings(candles, n=2):
    """Swing highs/lows : extrême local sur n bougies de chaque côté."""
    H = [float(c[2]) for c in candles]
    L = [float(c[3]) for c in candles]
    sh, sl = [], []
    for i in range(n, len(candles) - n):
        if H[i] == max(H[i - n:i + n + 1]):
            sh.append((i, H[i]))
        if L[i] == min(L[i - n:i + n + 1]):
            sl.append((i, L[i]))
    return sh, sl


def market_structure(candles):
    """Structure via les 2 derniers swings highs et lows."""
    sh, sl = _swings(candles)
    if len(sh) < 2 or len(sl) < 2:
        return {"trend": "INDÉTERMINÉ", "note": "pas assez de swings"}
    hh = sh[-1][1] > sh[-2][1]
    hl = sl[-1][1] > sl[-2][1]
    lh = sh[-1][1] < sh[-2][1]
    ll = sl[-1][1] < sl[-2][1]
    if hh and hl:
        return {"trend": "UPTREND", "note": "Higher Highs + Higher Lows", "last_sh": sh[-1][1], "last_sl": sl[-1][1]}
    if lh and ll:
        return {"trend": "DOWNTREND", "note": "Lower Highs + Lower Lows", "last_sh": sh[-1][1], "last_sl": sl[-1][1]}
    return {"trend": "RANGE", "note": "structure mixte", "last_sh": sh[-1][1], "last_sl": sl[-1][1]}


def detect_bos_choch(candles):
    """BOS (cassure dans le sens) ou CHoCH (cassure contre = reversal)."""
    sh, sl = _swings(candles)
    if len(sh) < 2 or len(sl) < 2:
        return None
    price = float(candles[-1][4])
    ms = market_structure(candles)
    trend = ms["trend"]
    last_sh = sh[-1][1]; last_sl = sl[-1][1]
    if trend == "UPTREND":
        if price > last_sh:
            return {"type": "BOS", "dir": "LONG", "level": round(last_sh, 2), "note": "BOS haussier — continuation uptrend"}
        if price < last_sl:
            return {"type": "CHoCH", "dir": "SHORT", "level": round(last_sl, 2), "note": "CHoCH baissier — possible retournement"}
    elif trend == "DOWNTREND":
        if price < last_sl:
            return {"type": "BOS", "dir": "SHORT", "level": round(last_sl, 2), "note": "BOS baissier — continuation downtrend"}
        if price > last_sh:
            return {"type": "CHoCH", "dir": "LONG", "level": round(last_sh, 2), "note": "CHoCH haussier — possible retournement"}
    return None


def find_fvg(candles, lookback=30):
    """Fair Value Gaps (imbalances 3 bougies) non comblés récents."""
    fvgs = []
    seg = candles[-lookback:]
    for i in range(1, len(seg) - 1):
        h0, l0 = float(seg[i - 1][2]), float(seg[i - 1][3])
        h2, l2 = float(seg[i + 1][2]), float(seg[i + 1][3])
        if l2 > h0:   # FVG haussier (gap up non comblé)
            fvgs.append({"type": "FVG_BULL", "low": round(h0, 2), "high": round(l2, 2), "dir": "LONG"})
        elif h2 < l0:  # FVG baissier
            fvgs.append({"type": "FVG_BEAR", "low": round(h2, 2), "high": round(l0, 2), "dir": "SHORT"})
    return fvgs[-3:]


def find_order_blocks(candles, lookback=30):
    """Order Blocks : dernière bougie opposée avant une impulsion forte."""
    seg = candles[-lookback:]
    obs = []
    for i in range(1, len(seg) - 1):
        o, c = float(seg[i][1]), float(seg[i][4])
        nxt_c = float(seg[i + 1][4]); nxt_o = float(seg[i + 1][1])
        body = abs(c - o); nxt_body = abs(nxt_c - nxt_o)
        # OB haussier : bougie baissière suivie d'une forte bougie haussière
        if c < o and nxt_c > nxt_o and nxt_body > body * 1.3:
            obs.append({"type": "OB_BULL", "low": round(float(seg[i][3]), 2),
                        "high": round(float(seg[i][2]), 2), "dir": "LONG"})
        if c > o and nxt_c < nxt_o and nxt_body > body * 1.3:
            obs.append({"type": "OB_BEAR", "low": round(float(seg[i][3]), 2),
                        "high": round(float(seg[i][2]), 2), "dir": "SHORT"})
    return obs[-2:]


def detect_liquidity(candles, lookback=30, tol=0.0008):
    """Equal highs/lows = pools de liquidité (stops accumulés, cibles institutionnelles)."""
    seg = candles[-lookback:]
    H = [float(c[2]) for c in seg]; L = [float(c[3]) for c in seg]
    pools = []
    hi = max(H); lo = min(L)
    eq_h = [h for h in H if abs(h - hi) / hi < tol]
    eq_l = [l for l in L if abs(l - lo) / lo < tol]
    if len(eq_h) >= 2:
        pools.append({"type": "BUY_SIDE_LIQ", "level": round(hi, 2), "note": "Equal highs = stops acheteurs au-dessus (cible)"})
    if len(eq_l) >= 2:
        pools.append({"type": "SELL_SIDE_LIQ", "level": round(lo, 2), "note": "Equal lows = stops vendeurs en-dessous (cible)"})
    return pools


def smc_analysis(candles):
    """Synthèse SMC : structure + BOS/CHoCH + OB + FVG + liquidité → biais + score."""
    if not candles or len(candles) < 15:
        return {"bias": "NEUTRAL", "score": 0, "signals": ["SMC: pas assez de bougies"], "concepts": []}
    ms = market_structure(candles)
    bos = detect_bos_choch(candles)
    obs = find_order_blocks(candles)
    fvgs = find_fvg(candles)
    liq = detect_liquidity(candles)
    price = float(candles[-1][4])

    signals, score, concepts = [], 0.0, []
    # Structure
    if ms["trend"] == "UPTREND":
        score += 0.8; signals.append(f"📈 Structure HAUSSIÈRE (HH/HL)"); concepts.append("UPTREND")
    elif ms["trend"] == "DOWNTREND":
        score -= 0.8; signals.append(f"📉 Structure BAISSIÈRE (LH/LL)"); concepts.append("DOWNTREND")
    else:
        signals.append("↔️ Structure en RANGE")
    # BOS / CHoCH
    if bos:
        d = 1 if bos["dir"] == "LONG" else -1
        if bos["type"] == "BOS":
            score += d * 0.7
        else:
            score += d * 0.9   # CHoCH = signal de reversal plus fort
        signals.append(f"🔑 {bos['type']} {bos['dir']} @ {bos['level']} — {bos['note']}")
        concepts.append(bos["type"])
    # Order block le plus proche
    if obs:
        ob = obs[-1]
        near = ob["low"] <= price <= ob["high"]
        tag = " ←← PRIX DANS L'OB" if near else ""
        signals.append(f"🟦 {ob['type']} {ob['low']}-{ob['high']}{tag}")
        concepts.append(ob["type"])
        if near:
            score += (0.6 if ob["dir"] == "LONG" else -0.6)
    # FVG le plus proche
    if fvgs:
        f = fvgs[-1]
        signals.append(f"⬜ {f['type']} {f['low']}-{f['high']} (imbalance à combler)")
        concepts.append(f["type"])
    # Liquidité
    for p in liq:
        signals.append(f"🎯 {p['type']} @ {p['level']} — {p['note']}")
        concepts.append(p["type"])

    bias = "LONG" if score >= 0.5 else ("SHORT" if score <= -0.5 else "NEUTRAL")
    return {"bias": bias, "score": round(score, 2), "signals": signals,
            "concepts": concepts, "structure": ms["trend"]}


if __name__ == "__main__":
    from tv_candles import TVCandleClient
    cl = TVCandleClient(symbols=["GOLD"], timeframe="15m", n_bars=100, timeout=25)
    cl.fetch_ta()
    candles = cl._candles.get("GOLD", [])
    r = smc_analysis(candles)
    print(f"\n🧠 SMC GOLD — biais {r['bias']} (score {r['score']}) — structure {r['structure']}\n")
    for s in r["signals"]:
        print(f"   {s}")
    print(f"\n   Concepts détectés : {r['concepts']}")
