#!/usr/bin/env python3
"""
AURUM — Internals OR (l'edge spécifique XAUUSD)
══════════════════════════════════════════════════════════════════
1. DXY MOMENTUM : corrélation inverse #1 de l'or (DXY↓ = OR↑)
2. RATIO OR/ARGENT : régime risk / confirmation des métaux
3. PROXY TAUX RÉELS : US10Y momentum (taux↑ = baissier or)
4. VIX : refuge (stress = support or)
Score positif = bullish OR, négatif = bearish.
"""
from tv_live import TVLiveClient
from tv_candles import SYMBOL_MAP

EDGE_SYMBOLS = [SYMBOL_MAP[a] for a in ["GOLD", "DXY", "SILVER", "US10Y", "VIX"]]


def fetch_internals():
    raw = TVLiveClient(symbols=EDGE_SYMBOLS, timeout=15).fetch()
    out = {}
    for short, d in raw.items():
        out[short] = {"price": d.get("lp"), "chg": d.get("chp", 0) or 0}
    return out


def analyze(internals):
    def p(k): return (internals.get(k, {}) or {}).get("price")
    def c(k): return (internals.get(k, {}) or {}).get("chg", 0) or 0
    signals, score = [], 0.0

    # DXY momentum (inverse #1)
    dxy_c = c("DXY")
    if dxy_c <= -0.3:
        score += 1.5; signals.append(f"🟢 DXY {dxy_c:+.2f}% ↓↓ → dollar faible = HAUSSIER or (corrélation inverse #1)")
    elif dxy_c <= -0.1:
        score += 0.7; signals.append(f"🟢 DXY {dxy_c:+.2f}% ↓ → léger soutien or")
    elif dxy_c >= 0.3:
        score -= 1.5; signals.append(f"🔴 DXY {dxy_c:+.2f}% ↑↑ → dollar fort = BAISSIER or")
    elif dxy_c >= 0.1:
        score -= 0.7; signals.append(f"🔴 DXY {dxy_c:+.2f}% ↑ → léger frein or")
    else:
        signals.append(f"⚪ DXY {dxy_c:+.2f}% plat → corrélation inverse inactive")

    # Ratio or/argent (régime risk) — INFO + petit score régime
    g, s = p("GOLD"), p("SILVER")
    silver_c = c("SILVER"); gold_c = c("GOLD")
    if g and s:
        ratio = g / s
        regime = "RISK-OFF (or surperforme)" if ratio >= 88 else ("RISK-ON (argent surperforme)" if ratio <= 72 else "neutre")
        signals.append(f"⚪ Ratio or/argent {ratio:.1f} → {regime}")
    # Silver : INFO seulement (la couche MACRO score déjà l'argent — pas de double comptage)
    if abs(gold_c) > 0.1:
        if (gold_c > 0) == (silver_c > 0):
            signals.append(f"🟢 Argent {silver_c:+.2f}% confirme l'or ({gold_c:+.2f}%)")
        else:
            signals.append(f"🟠 Argent {silver_c:+.2f}% DIVERGE de l'or → move fragile")

    # Taux : INFO seulement (la couche MACRO score déjà US10Y — pas de double comptage)
    y = c("US10Y")
    signals.append(f"{'🔴' if y>=0.4 else ('🟢' if y<=-0.5 else '⚪')} Taux 10Y {y:+.2f}% (scoré dans la couche macro)")

    # VIX refuge
    vix_p, vix_c = p("VIX"), c("VIX")
    if vix_c >= 8:
        score += 0.6; signals.append(f"🟢 VIX {vix_c:+.1f}% ↑↑ → stress = demande refuge or")
    elif vix_p and vix_p < 13:
        signals.append(f"⚪ VIX bas {vix_p:.1f} → pas de demande refuge")

    direction = "LONG" if score >= 0.5 else ("SHORT" if score <= -0.5 else "NEUTRAL")
    return {"score": round(score, 2), "direction": direction, "signals": signals,
            "dxy_chg": dxy_c, "silver_chg": silver_c, "y_chg": y,
            "gold_silver_ratio": round(g / s, 1) if (g and s) else None}


def full_edge():
    return analyze(fetch_internals())


if __name__ == "__main__":
    e = full_edge()
    print(f"\n🥇 INTERNALS OR — score {e['score']:+.2f} {e['direction']}\n")
    for s in e["signals"]:
        print(f"   {s}")
