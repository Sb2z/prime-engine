#!/usr/bin/env python3
"""
SENTINEL-500, Moteur macro S&P 500
Corrélations ACTIONS (signes cohérents, pas les paradoxes de l'or) :
  • VIX      : inverse fort (-0.8), VIX↑ = S&P↓
  • US10Y    : taux↑ = pression (surtout tech/growth)
  • DXY      : dollar fort = léger frein (multinationales)
  • NAS100   : leader (+0.9), la tech mène l'indice
  • OIL      : pétrole↑ = inflation = léger frein
Score positif = bullish S&P, négatif = bearish.
"""

from tv_live import TVLiveClient
from tv_candles import SYMBOL_MAP

MACRO_SYMBOLS = [SYMBOL_MAP[a] for a in ["VIX", "US10Y", "DXY", "NAS100", "OIL", "US500"]]


def fetch_macro_data() -> dict:
    results = {}
    try:
        raw = TVLiveClient(symbols=MACRO_SYMBOLS, timeout=14).fetch()
        m = {"VIX": "VIX", "US10Y": "US10Y", "DXY": "DXY", "US100": "NAS100",
             "USOIL": "OIL", "US500": "US500"}
        for short, d in raw.items():
            name = m.get(short, short)
            results[name] = {"price": d.get("lp"), "chg": d.get("chp", 0) or 0, "raw": d}
    except Exception as e:
        results["error"] = str(e)
    return results


def score_macro_confluence(macro: dict) -> dict:
    """Score macro pour S&P. Positif = bullish, négatif = bearish."""
    signals, total = [], 0.0

    def chg(k):
        return (macro.get(k, {}) or {}).get("chg", 0) or 0
    def price(k):
        return (macro.get(k, {}) or {}).get("price")

    # VIX (inverse, le plus important)
    vix_c, vix_p = chg("VIX"), price("VIX") or 0
    if vix_c <= -3:
        s = +1.5; signals.append(("VIX", f"VIX {vix_c:+.1f}% ↓ → risk-on, bullish", s))
    elif vix_c >= 5:
        s = -2.5; signals.append(("VIX", f"VIX {vix_c:+.1f}% ↑↑ → risk-off fort, bearish", s))
    elif vix_c >= 2:
        s = -1.5; signals.append(("VIX", f"VIX {vix_c:+.1f}% ↑ → stress, bearish", s))
    else:
        s = 0.0; signals.append(("VIX", f"VIX {vix_p:.1f} ({vix_c:+.1f}%) neutre", s))
    if vix_p >= 22:
        s -= 0.5; signals.append(("VIX_abs", f"VIX absolu élevé {vix_p:.1f} → prudence", -0.5))
    total += s

    # NAS100 (leader)
    nq = chg("NAS100")
    if nq >= 0.3:
        s = +1.0; signals.append(("NAS100", f"NASDAQ {nq:+.2f}% → la tech mène, bullish", s))
    elif nq <= -0.3:
        s = -1.0; signals.append(("NAS100", f"NASDAQ {nq:+.2f}% → tech faible, bearish", s))
    else:
        s = 0.0; signals.append(("NAS100", f"NASDAQ {nq:+.2f}% neutre", s))
    total += s

    # US10Y (taux)
    y = chg("US10Y")
    if y >= 1.0:
        s = -1.5; signals.append(("US10Y", f"Taux 10Y {y:+.2f}% ↑↑ → pression valorisations, bearish", s))
    elif y >= 0.4:
        s = -0.8; signals.append(("US10Y", f"Taux 10Y {y:+.2f}% ↑ → léger frein", s))
    elif y <= -0.5:
        s = +0.6; signals.append(("US10Y", f"Taux 10Y {y:+.2f}% ↓ → soutien actions", s))
    else:
        s = 0.0; signals.append(("US10Y", f"Taux 10Y {y:+.2f}% neutre", s))
    total += s

    # DXY (dollar)
    dx = chg("DXY")
    if dx >= 0.5:
        s = -0.5; signals.append(("DXY", f"Dollar {dx:+.2f}% ↑ → frein multinationales", s))
    elif dx <= -0.5:
        s = +0.3; signals.append(("DXY", f"Dollar {dx:+.2f}% ↓ → léger soutien", s))
    else:
        s = 0.0; signals.append(("DXY", f"Dollar {dx:+.2f}% neutre", s))
    total += s

    # OIL (inflation)
    oil = chg("OIL")
    if oil >= 3:
        s = -0.5; signals.append(("OIL", f"Pétrole {oil:+.1f}% ↑ → pression inflation", s))
    else:
        s = 0.0
    total += s

    direction = "LONG" if total >= 0.5 else ("SHORT" if total <= -0.5 else "NEUTRAL")
    return {"score": round(total, 2), "direction": direction, "signals": signals}


def macro_regime(macro: dict) -> str:
    def chg(k): return (macro.get(k, {}) or {}).get("chg", 0) or 0
    def price(k): return (macro.get(k, {}) or {}).get("price") or 0
    vix_c, vix_p, nq, y, dx = chg("VIX"), price("VIX"), chg("NAS100"), chg("US10Y"), chg("DXY")

    if vix_p >= 22 or vix_c >= 5:
        return "RISK_OFF"                      # stress = vendre
    if vix_p <= 16 and vix_c <= 0 and nq >= 0.2:
        return "RISK_ON_BULL"                  # peur basse + tech mène = idéal long
    if y >= 0.5 and dx >= 0.3:
        return "RATE_FEAR"                     # taux + dollar montent = pression
    if abs(vix_c) < 1 and abs(nq) < 0.2 and abs(y) < 0.3:
        return "CONSOLIDATION"
    return "MIXED"


if __name__ == "__main__":
    import json
    m = fetch_macro_data()
    print(json.dumps({k: {"price": v.get("price"), "chg": v.get("chg")} for k, v in m.items() if isinstance(v, dict)}, indent=2))
    print("\nScore:", score_macro_confluence(m))
    print("Régime:", macro_regime(m))
