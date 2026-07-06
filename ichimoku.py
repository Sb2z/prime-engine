#!/usr/bin/env python3
"""ICHIMOKU — features additives pour le feature store (phase enregistrement).

Hypothèse de Sam (11/06/2026) : le nuage Ichimoku apporte de l'information.
On ENREGISTRE sans rien décider — comme le COT. Dans quelques semaines, la
corrélation aux outcomes dira si ces colonnes prédisent quoi que ce soit une
fois le régime ER/ADX connu (redondance suspectée pour les distances
Tenkan/Kijun vs EMA ; épaisseur du Kumo / position ternaire / twist sont les
candidats à de l'information nouvelle).

Le CALCUL vit dans strategy_families.ichimoku_state (fichier protégé, source
unique juge/production) — ce module n'est qu'une projection en colonnes,
normalisée ATR. Anti-lookahead prouvé par test_ichimoku.py.

Échec réseau/calcul → {} : record_cycle insère des NULL, jamais un cycle
planté.
"""

N_BARS = 140          # >= 52 + 26 + marge (twist_age + ATR)
ATR_N = 14
TFS = {"15m": "ichi15", "1h": "ichi1h"}


def _atr(window, n=ATR_N):
    """ATR simple (moyenne des True Ranges) sur les n dernières bougies."""
    if len(window) < n + 1:
        return None
    trs = []
    for i in range(len(window) - n, len(window)):
        h, l = float(window[i][2]), float(window[i][3])
        pc = float(window[i - 1][4])
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    atr = sum(trs) / n
    return atr if atr > 0 else None


def features_from_window(window):
    """Dict de 8 features Ichimoku (sans préfixe tf) connues à window[-1]."""
    import strategy_families as sf
    s = sf.ichimoku_state(window, "standard")
    atr = _atr(window)
    if s is None or atr is None:
        return {}
    close = s["close"]
    if close > s["cloud_top"]:
        pos, d_cloud = 1, (close - s["cloud_top"]) / atr
    elif close < s["cloud_bot"]:
        pos, d_cloud = -1, (close - s["cloud_bot"]) / atr
    else:
        pos, d_cloud = 0, 0.0
    return {
        "pos": pos,
        "d_tenkan": (close - s["tenkan"]) / atr,
        "d_kijun": (close - s["kijun"]) / atr,
        "d_cloud": d_cloud,
        "kumo_atr": (s["cloud_top"] - s["cloud_bot"]) / atr,
        "tk_atr": (s["tenkan"] - s["kijun"]) / atr,
        "twist_age": s["twist_age"],
        "chikou": s["chikou"],
    }


def snapshot(asset):
    """Features Ichimoku 15m + 1h pour un actif, préfixées par timeframe.

    Retourne {} (jamais d'exception) si les bougies manquent : les colonnes
    restent NULL pour ce cycle.
    """
    out = {}
    try:
        import datafeed
        for tf, prefix in TFS.items():
            res = datafeed.get_candles(asset, tf=tf, n=N_BARS)
            candles = (res or {}).get("candles") or []
            feats = features_from_window(candles) if candles else {}
            for k, v in feats.items():
                out[f"{prefix}_{k}"] = v
    except Exception:
        return {}
    return out


if __name__ == "__main__":
    import json
    for asset in ("GOLD", "US500"):
        print(asset, json.dumps(snapshot(asset), indent=1))
