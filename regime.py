#!/usr/bin/env python3
"""
REGIME, Détecteur de régime de marché (ton filtre "scalper ou pas")
══════════════════════════════════════════════════════════════════
Explique pourquoi Sam fait 89% un jour et 45% le lendemain avec LA MÊME stratégie :
ce n'est pas la stratégie, c'est le RÉGIME.

Efficiency Ratio (Kaufman) = |move net| / |chemin total parcouru|
  • ER élevé (>0.45) + ADX fort = TENDANCE PROPRE (one-way) → scalp-rebond GAGNE (89%)
  • ER faible (<0.30) + ADX fort = TENDANCE HACHÉE (whipsaw) → scalp PERD (45%)
  • ADX faible = RANGE → ne pas scalper

Verdict actionnable : "JOUR PROPRE (scalpe fort)" vs "HACHÉ (réduis/stop)".
"""


def efficiency_ratio(closes, n=None):
    n = n or len(closes) - 1
    if len(closes) < n + 1:
        return None
    net = abs(closes[-1] - closes[-1 - n])
    path = sum(abs(closes[i] - closes[i - 1]) for i in range(len(closes) - n, len(closes)))
    return round(net / path, 3) if path else 0


def detect(candles, adx=None, lookback=40):
    """Classe le régime sur les dernières bougies. adx = ADX courant (optionnel)."""
    if not candles or len(candles) < 15:
        return {"regime": "INDÉTERMINÉ", "er": None, "scalp_ok": False, "note": "pas assez de données"}
    closes = [float(c[4]) for c in candles[-lookback:]]
    er = efficiency_ratio(closes)

    # Volatilité réalisée (amplitude moyenne) pour le contexte
    rng = sum((float(c[2]) - float(c[3])) for c in candles[-lookback:]) / lookback

    a = adx if adx is not None else 0

    if a >= 25 and er >= 0.45:
        regime, scalp, wr = "TENDANCE PROPRE 🟢", True, "~85-90% (ton jour vendredi)"
        note = "One-way directionnel, les rebonds échouent → SCALPE FORT dans le sens"
    elif a >= 25 and er <= 0.30:
        regime, scalp, wr = "TENDANCE HACHÉE 🔴", False, "~45% (ton jour lundi)"
        note = "Tendance mais whipsaw, les rebonds piègent → RÉDUIS ou STOP"
    elif a >= 22 and er > 0.30:
        # ADX modéré (22-25) OU ADX≥25 à ER intermédiaire : tendance correcte. Le
        # cas ER≥0.45 à ADX≥25 est déjà capté par la branche PROPRE plus haut ; ici
        # on inclut ER≥0.45 à 22≤ADX<25 (mouvement directionnel propre mais ADX
        # modéré) qui tombait à tort en TRANSITION « ambigu » (correctif 2026-06-18).
        regime, scalp, wr = "TENDANCE MOYENNE 🟡", True, "~60%"
        note = "Tendance correcte mais bruitée, scalp SÉLECTIF, taille réduite"
    elif a < 18:
        regime, scalp, wr = "RANGE ⚪", False, "~33% (tes pertes)"
        note = "Pas de tendance, NE PAS SCALPER, c'est là que tu perds"
    else:
        regime, scalp, wr = "TRANSITION 🟡", False, "incertain"
        note = "Régime ambigu, attendre la clarification"

    return {"regime": regime, "er": er, "adx": round(a, 1), "avg_range": round(rng, 2),
            "scalp_ok": scalp, "expected_wr": wr, "note": note}


if __name__ == "__main__":
    from tv_candles import TVCandleClient
    for sym in ["GOLD", "US500"]:
        cl = TVCandleClient(symbols=[sym], timeframe="15m", n_bars=60, timeout=22)
        cl.fetch_ta()
        ta = cl.fetch_ta().get(sym, {}) if False else None
        cl2 = TVCandleClient(symbols=[sym], timeframe="15m", n_bars=60, timeout=22)
        adx = cl2.fetch_ta().get(sym, {}).get("adx")
        r = detect(cl._candles.get(sym, []), adx=adx)
        print(f"\n📐 RÉGIME {sym} : {r['regime']}")
        print(f"   ER {r['er']} · ADX {r['adx']} · scalp_ok {r['scalp_ok']} · WR attendu {r['expected_wr']}")
        print(f"   → {r['note']}")
