#!/usr/bin/env python3
"""
ORDERFLOW — "Order flow du pauvre" calculé depuis les bougies (gratuit)
══════════════════════════════════════════════════════════════════
~60-70% de l'edge order flow sans flux CME payant :
  • VOLUME PROFILE : distribution du volume par niveau de prix
  • POINT OF CONTROL (POC) : le prix au plus gros volume = aimant S/R #1
  • VALUE AREA (VAH/VAL) : zone des ~70% du volume = "juste valeur"
  • VWAP : prix moyen pondéré volume (référence institutionnelle)
  • CUMULATIVE DELTA (proxy) : pression acheteur/vendeur via position de clôture
  • DIVERGENCE delta/prix : faiblesse cachée (prix monte, delta baisse)

⚠️ Volume = CFD/synthétique (TradingView), pas le vrai DOM exchange. Proxy, pas vérité absolue.
"""


def _vol(c):
    """Volume de la bougie ; fallback 1 si absent (devient profil temps/prix TPO)."""
    try:
        v = float(c[5]) if len(c) > 5 and c[5] else 0.0
    except Exception:
        v = 0.0
    return v if v > 0 else 0.0


def volume_profile(candles, bins=40):
    """Profil de volume → POC, Value Area (VAH/VAL), HVN/LVN."""
    if len(candles) < 10:
        return None
    lo = min(float(c[3]) for c in candles)
    hi = max(float(c[2]) for c in candles)
    if hi <= lo:
        return None
    step = (hi - lo) / bins
    profile = [0.0] * bins
    total_vol = sum(_vol(c) for c in candles)
    use_time = total_vol <= 0    # si pas de volume → profil temps (1 par bougie)

    for c in candles:
        ch, cl = float(c[2]), float(c[3])
        v = 1.0 if use_time else _vol(c)
        b0 = max(0, int((cl - lo) / step))
        b1 = min(bins - 1, int((ch - lo) / step))
        span = (b1 - b0 + 1) or 1
        for b in range(b0, b1 + 1):
            profile[b] += v / span

    poc_bin = max(range(bins), key=lambda b: profile[b])
    poc = round(lo + (poc_bin + 0.5) * step, 2)

    # Value Area : étendre depuis le POC jusqu'à 70% du volume
    tot = sum(profile)
    target = tot * 0.70
    lo_b = hi_b = poc_bin
    acc = profile[poc_bin]
    while acc < target and (lo_b > 0 or hi_b < bins - 1):
        below = profile[lo_b - 1] if lo_b > 0 else -1
        above = profile[hi_b + 1] if hi_b < bins - 1 else -1
        if above >= below:
            hi_b += 1; acc += max(above, 0)
        else:
            lo_b -= 1; acc += max(below, 0)
    val = round(lo + lo_b * step, 2)
    vah = round(lo + (hi_b + 1) * step, 2)

    # High/Low volume nodes
    avg = tot / bins
    hvn = [round(lo + (b + 0.5) * step, 2) for b in range(bins) if profile[b] > avg * 1.6]
    lvn = [round(lo + (b + 0.5) * step, 2) for b in range(bins) if 0 < profile[b] < avg * 0.4]

    return {"poc": poc, "vah": vah, "val": val,
            "hvn": hvn[:4], "lvn": lvn[:4],
            "mode": "TIME" if use_time else "VOLUME"}


def session_vwap(candles):
    """VWAP pondéré volume (ou moyenne typique si pas de volume)."""
    if not candles:
        return None
    cum_pv = cum_v = 0.0
    tps = []
    for c in candles:
        tp = (float(c[2]) + float(c[3]) + float(c[4])) / 3
        tps.append(tp)
        v = _vol(c)
        cum_pv += tp * v; cum_v += v
    return round(cum_pv / cum_v, 2) if cum_v > 0 else round(sum(tps) / len(tps), 2)


def cumulative_delta(candles):
    """
    Cumulative delta proxy : pression via la position de clôture dans la bougie.
    delta ≈ volume × (2·(close-low)/(high-low) − 1)  (close haut = acheteurs).
    Retourne delta cumulé + détection de divergence prix/delta.
    """
    if len(candles) < 10:
        return None
    cum = 0.0; series = []
    for c in candles:
        h, l, cl = float(c[2]), float(c[3]), float(c[4])
        rng = (h - l) or 0.01
        loc = (2 * (cl - l) / rng) - 1     # -1 (close au low) à +1 (close au high)
        v = _vol(c) or 1.0
        cum += v * loc
        series.append(cum)
    # Divergence : prix vs delta cumulé sur les 10 dernières bougies
    n = min(10, len(candles))
    price_chg = float(candles[-1][4]) - float(candles[-n][4])
    delta_chg = series[-1] - series[-n]
    div = None
    if price_chg > 0 and delta_chg < 0:
        div = "BEARISH_DIV (prix↑ mais delta↓ = achat faible)"
    elif price_chg < 0 and delta_chg > 0:
        div = "BULLISH_DIV (prix↓ mais delta↑ = vente faible)"
    bias = "LONG" if delta_chg > 0 else ("SHORT" if delta_chg < 0 else "NEUTRAL")
    return {"cum_delta": round(series[-1], 1), "recent_delta": round(delta_chg, 1),
            "bias": bias, "divergence": div}


def analyze(candles):
    """Synthèse order flow : VP + VWAP + delta → niveaux clés + biais + score."""
    vp = volume_profile(candles)
    vwap = session_vwap(candles)
    delta = cumulative_delta(candles)
    if not vp or not candles:
        return {"signals": ["Order flow: pas assez de données"], "score": 0, "poc": None, "vwap": vwap}
    price = float(candles[-1][4])
    signals, score = [], 0.0

    # POC = aimant principal
    rel_poc = "au-dessus" if price > vp["poc"] else "en-dessous"
    signals.append(f"🎯 POC {vp['poc']} (prix {rel_poc}) — aimant S/R #1")
    # Value Area
    if price > vp["vah"]:
        score += 0.4; signals.append(f"🟢 Prix > VAH {vp['vah']} → au-dessus de la valeur (acheteur)")
    elif price < vp["val"]:
        score -= 0.4; signals.append(f"🔴 Prix < VAL {vp['val']} → sous la valeur (vendeur)")
    else:
        signals.append(f"⚪ Dans la Value Area {vp['val']}–{vp['vah']} (équilibre)")
    # VWAP
    if vwap:
        if price > vwap:
            score += 0.3; signals.append(f"🟢 Prix > VWAP {vwap} → biais acheteur")
        else:
            score -= 0.3; signals.append(f"🔴 Prix < VWAP {vwap} → biais vendeur")
    # Delta
    if delta:
        d = 0.4 if delta["bias"] == "LONG" else (-0.4 if delta["bias"] == "SHORT" else 0)
        score += d
        signals.append(f"{'🟢' if d>0 else '🔴' if d<0 else '⚪'} Cumulative delta {delta['recent_delta']:+.0f} ({delta['bias']})")
        if delta["divergence"]:
            signals.append(f"⚠️ {delta['divergence']}")
            score += -0.5 if "BEARISH" in delta["divergence"] else 0.5
    # LVN proches = zones de cassure rapide
    if vp["lvn"]:
        signals.append(f"⬜ LVN (vide de volume, cassure rapide) : {vp['lvn'][:2]}")

    bias = "LONG" if score >= 0.4 else ("SHORT" if score <= -0.4 else "NEUTRAL")
    return {"signals": signals, "score": round(score, 2), "bias": bias,
            "poc": vp["poc"], "vah": vp["vah"], "val": vp["val"],
            "vwap": vwap, "lvn": vp["lvn"], "hvn": vp["hvn"],
            "mode": vp["mode"], "delta": delta}


if __name__ == "__main__":
    from tv_candles import TVCandleClient
    for sym in ["GOLD", "US500"]:
        cl = TVCandleClient(symbols=[sym], timeframe="15m", n_bars=120, timeout=25)
        cl.fetch_ta()
        r = analyze(cl._candles.get(sym, []))
        print(f"\n📊 ORDER FLOW {sym} — biais {r.get('bias')} (score {r.get('score')}) [{r.get('mode')}]")
        for s in r["signals"]:
            print(f"   {s}")
