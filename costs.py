#!/usr/bin/env python3
"""COSTS, coûts de transaction CFD appliqués à la mesure.

Le journal clôturait à exit_price = tp1/stop exact : zéro spread, slippage,
swap. Les trades USER sont des fills réels Revolut, la comparaison était
biaisée en faveur de l'IA. Ce module centralise des coûts de départ prudents
(CFD retail), à calibrer plus tard sur les tickets d'exécution réels.

Toutes les corrections DÉGRADENT le pnl, jamais l'inverse.
"""

import datetime as dt
import tz

# Points par actif. spread_off = sessions mortes (spreads élargis).
COSTS = {
    "GOLD":  {"spread_session": 0.50, "spread_off": 1.20, "slippage_stop": 0.30, "swap_pct_per_night": 0.012},
    "US500": {"spread_session": 1.50, "spread_off": 4.00, "slippage_stop": 1.00, "swap_pct_per_night": 0.010},
}

# Fallback en % du prix pour un actif non listé.
FALLBACK_PCT = {"spread_session": 0.020, "spread_off": 0.050, "slippage_stop": 0.015, "swap_pct_per_night": 0.010}

OFF_SESSIONS = {"CLOSED", "WEEKEND", "OVERNIGHT"}


def _points(asset, key, price):
    c = COSTS.get(asset)
    if c:
        return c[key]
    return (price or 0) * FALLBACK_PCT[key] / 100


def spread_points(asset, session, price=None):
    key = "spread_off" if (session or "").upper() in OFF_SESSIONS else "spread_session"
    return _points(asset, key, price)


def slippage_points(asset, price=None):
    return _points(asset, "slippage_stop", price)


def swap_pct(asset, nights):
    if nights <= 0:
        return 0.0
    c = COSTS.get(asset)
    per_night = c["swap_pct_per_night"] if c else FALLBACK_PCT["swap_pct_per_night"]
    return per_night * nights


def nights_held(open_ts_iso, close_ts_iso):
    """Nombre de minuits (Paris) traversés entre l'ouverture et la clôture."""
    try:
        o = dt.datetime.fromisoformat(open_ts_iso)
        c = dt.datetime.fromisoformat(close_ts_iso)
    except Exception:
        return 0
    return max(0, (tz.to_paris(c).date() - tz.to_paris(o).date()).days)


def adjust_exit(asset, level, direction, session, kind):
    """Prix de sortie dégradé. kind: 'tp' | 'market' (spread) ou 'sl' (slippage).

    sign tel que LONG sort plus bas et SHORT sort plus haut que le niveau brut.
    """
    sign = 1 if direction == "LONG" else -1
    if kind == "sl":
        return level - sign * slippage_points(asset, level)
    return level - sign * spread_points(asset, session, level)


def adjust_entry(asset, level, direction, session):
    """Fill MARKET à l'ENTRÉE : on paie le spread du mauvais côté (LONG achète à
    l'ask = plus haut, SHORT vend au bid = plus bas). Symétrique d'adjust_exit, sans ça le juge ne facturait que la MOITIÉ du spread aller-retour (audit 06-18).
    NB : ne concerne QUE le backtest (entrées market) ; le live utilise des entrées
    LIMITE OTE qui fillent AU niveau (pas de spread à l'entrée) -> journal inchangé."""
    sign = 1 if direction == "LONG" else -1
    return level + sign * spread_points(asset, session, level)


def calibrate_from_user_trades():
    """Stub : ajuster COSTS depuis les fills réels Revolut (prix demandé vs
    exécuté sur les tickets de Sam). À implémenter quand les tickets seront
    exportés."""
    raise NotImplementedError("calibration sur fills réels pas encore disponible")


if __name__ == "__main__":
    for asset in COSTS:
        print(asset, COSTS[asset])
    print("US500 SHORT TP 7500 session NY :", adjust_exit("US500", 7500, "SHORT", "NY", "tp"))
    print("US500 SHORT SL 7580            :", adjust_exit("US500", 7580, "SHORT", "NY", "sl"))
    print("GOLD LONG TP 3350 CLOSED       :", adjust_exit("GOLD", 3350, "LONG", "CLOSED", "tp"))
    print("nights 2026-06-05T22:00 → 2026-06-07T01:00 :",
          nights_held("2026-06-05T22:00:00+00:00", "2026-06-07T01:00:00+00:00"))
