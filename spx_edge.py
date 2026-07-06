#!/usr/bin/env python3
"""
SENTINEL-500, Internals de marché (l'edge institutionnel)
══════════════════════════════════════════════════════════════════
1. TERM STRUCTURE VIX : VIX9D / VIX / VIX3M / VVIX
   Contango (calme) vs Backwardation (stress), détecte la peur AVANT le prix.
2. BREADTH : S&P vs Russell 2000 vs Dow vs Equal-Weight
   Rallye large (sain) vs étroit (mega-caps, fragile).
Scores positifs = bullish S&P, négatifs = bearish.
"""

from tv_live import TVLiveClient
from tv_candles import SYMBOL_MAP

EDGE_SYMBOLS = [SYMBOL_MAP[a] for a in ["VIX9D", "VIX", "VIX3M", "VVIX", "US500", "RUT", "DJI", "RSP"]]


def fetch_internals() -> dict:
    raw = TVLiveClient(symbols=EDGE_SYMBOLS, timeout=15).fetch()
    out = {}
    for short, d in raw.items():
        out[short] = {"price": d.get("lp"), "chg": d.get("chp", 0) or 0}
    return out


def analyze_vix_structure(internals: dict) -> dict:
    """Term structure VIX → régime de volatilité + score."""
    def p(k): return (internals.get(k, {}) or {}).get("price")
    vix9, vix, vix3, vvix = p("VIX9D"), p("VIX"), p("VIX3M"), p("VVIX")
    signals, score, regime = [], 0.0, "INDÉTERMINÉ"

    if vix and vix3:
        ratio = vix / vix3
        if ratio >= 1.0:
            regime = "BACKWARDATION"; score -= 1.3
            signals.append(f"🔴 Backwardation VIX/VIX3M={ratio:.2f} → STRESS aigu, risk-off (peut marquer un bas de capitulation)")
        elif ratio <= 0.85:
            regime = "CONTANGO_STEEP"; score += 0.5
            signals.append(f"🟢 Contango fort {ratio:.2f} → marché calme, porteur (⚠️ complaisance si extrême)")
        else:
            regime = "CONTANGO_NORMAL"; score += 0.2
            signals.append(f"⚪ Contango normal {ratio:.2f} → conditions stables")

    if vix9 and vix:
        r2 = vix9 / vix
        if r2 >= 1.05:
            score -= 0.6
            signals.append(f"🔴 VIX9D>VIX ({r2:.2f}) → peur immédiate, événement court terme")

    if vvix:
        if vvix >= 100:
            score -= 0.5
            signals.append(f"🔴 VVIX {vvix:.0f} élevé → demande de couverture (tail risk)")
        elif vvix <= 85:
            score += 0.2
            signals.append(f"🟢 VVIX {vvix:.0f} bas → pas de panique sur la vol")

    return {"regime": regime, "score": round(score, 2), "signals": signals,
            "vix9d": vix9, "vix": vix, "vix3m": vix3, "vvix": vvix}


def analyze_breadth(internals: dict) -> dict:
    """Participation : S&P vs small caps vs Dow vs equal-weight."""
    def c(k): return (internals.get(k, {}) or {}).get("chg", 0) or 0
    spx, rut, dji, rsp = c("US500"), c("RUT"), c("DJI"), c("RSP")
    signals, score = [], 0.0

    # Divergence small caps (Russell) = le meilleur signal de largeur
    div = rut - spx
    if spx > 0.1 and rut < -0.1:
        score -= 0.8
        signals.append(f"🔴 Rallye ÉTROIT : S&P {spx:+.2f}% mais Russell {rut:+.2f}% → mega-caps seules, fragile")
    elif spx > 0.1 and rut > spx:
        score += 0.6
        signals.append(f"🟢 Rallye LARGE : Russell {rut:+.2f}% > S&P {spx:+.2f}% → participation saine")
    elif spx < -0.1 and rut < spx:
        score -= 0.5
        signals.append(f"🔴 Vente LARGE : Russell {rut:+.2f}% < S&P {spx:+.2f}% → risk-off généralisé")
    else:
        signals.append(f"⚪ Participation neutre (S&P {spx:+.2f}% / Russell {rut:+.2f}%)")

    # Equal-weight vs cap-weight
    if rsp and spx:
        if spx > 0.1 and rsp < spx - 0.2:
            score -= 0.3
            signals.append(f"🟠 Equal-weight {rsp:+.2f}% < S&P → concentration mega-caps")
        elif rsp > spx + 0.1:
            score += 0.2
            signals.append(f"🟢 Equal-weight {rsp:+.2f}% mène → largeur confirmée")

    return {"score": round(score, 2), "signals": signals,
            "spx": spx, "rut": rut, "dji": dji, "rsp": rsp}


def full_edge() -> dict:
    internals = fetch_internals()
    vix = analyze_vix_structure(internals)
    breadth = analyze_breadth(internals)
    total = round(vix["score"] + breadth["score"], 2)
    direction = "LONG" if total >= 0.5 else ("SHORT" if total <= -0.5 else "NEUTRAL")
    return {"internals": internals, "vix_structure": vix, "breadth": breadth,
            "score": total, "direction": direction}


if __name__ == "__main__":
    e = full_edge()
    print(f"\n🛡️ INTERNALS, score {e['score']:+.2f} {e['direction']}\n")
    print(f"  TERM STRUCTURE VIX, régime {e['vix_structure']['regime']}")
    for s in e["vix_structure"]["signals"]:
        print(f"   {s}")
    print(f"\n  BREADTH")
    for s in e["breadth"]["signals"]:
        print(f"   {s}")
