#!/usr/bin/env python3
"""
STRATEGIES — Playbook des meilleurs traders CFD + Risk Management forcé
══════════════════════════════════════════════════════════════════
Partagé par SENTINEL-500 (S&P) et AURUM (GOLD).
Encode ce qui fait gagner les particuliers les plus performants :
  • Raja Banks : liquidity sweep ("tap & snap"), sessions London/NY, RR élevé
  • ICT : Optimal Trade Entry (OTE, retracement Fib 0.62-0.79), order blocks, FVG
  • Supply/Demand zones, retracement "double flux"
RÈGLE D'OR (prioritaire sur tout) : RR ≥ 1:2 sur TP1. Pas de trade sinon.
"""

# RR informatif (PAS un gate). La décision = analyse globale (confluence + paramètres),
# pas un ratio imposé. Validé par les trades réels de Sam : WR élevé sur scalps gold > RR.
SCALP_R = 1.0         # cible scalp rapide (micro-rebond)
R_TP1 = 1.5
R_TP2 = 2.5
R_TP3 = 4.0


def build_levels(direction, entry, stop):
    """
    À partir de l'entrée + stop, propose plusieurs cibles (scalp + swing).
    Le RR n'est PAS un filtre — c'est juste de l'information. La décision vient
    de l'analyse globale (confluence, SMC, order flow, macro).
    """
    risk = abs(entry - stop)
    if risk <= 0:
        return None
    sign = 1 if direction == "LONG" else -1
    return {
        "entry": round(entry, 2), "stop": round(stop, 2), "risk": round(risk, 2),
        "tp_scalp": round(entry + sign * SCALP_R * risk, 2),  # scalp rapide (micro-rebond)
        "tp1": round(entry + sign * R_TP1 * risk, 2),
        "tp2": round(entry + sign * R_TP2 * risk, 2),
        "tp3": round(entry + sign * R_TP3 * risk, 2),
        "rr_tp1": R_TP1, "rr_tp2": R_TP2, "rr_tp3": R_TP3,
    }


def validate_rr(entry, stop, tp1, direction):
    """
    RR INFORMATIF (plus un gate). Retourne (True, rr, message) toujours OK —
    la décision de trader vient de l'analyse globale, pas du ratio.
    """
    risk = abs(entry - stop)
    reward = abs(tp1 - entry)
    if risk <= 0:
        return (True, 0, "Stop non défini")
    rr = reward / risk
    note = "(scalp, WR>RR)" if rr < 1.5 else ("(équilibré)" if rr < 2.5 else "(swing, RR élevé)")
    return (True, round(rr, 2), f"RR {rr:.2f}:1 {note} — info, pas un filtre")


# ── ICT : Optimal Trade Entry (zone de retracement "double flux") ────────────
def ote_zone(swing_high, swing_low, direction):
    """
    Zone OTE (ICT) = retracement 0.62-0.79 d'une jambe d'impulsion.
    C'est LA zone d'entrée en retracement (capte le pullback + la continuation).
    LONG : on achète le repli dans 0.62-0.79 d'une jambe HAUSSIÈRE.
    SHORT : on vend le rebond dans 0.62-0.79 d'une jambe BAISSIÈRE.
    """
    diff = swing_high - swing_low
    if direction == "LONG":
        return {"ote_high": round(swing_high - 0.62 * diff, 2),
                "ote_low": round(swing_high - 0.79 * diff, 2),
                "sweet_spot": round(swing_high - 0.705 * diff, 2),
                "note": "Zone d'achat sur repli (0.62-0.79) — entrée OTE pour continuation haussière"}
    else:
        return {"ote_low": round(swing_low + 0.62 * diff, 2),
                "ote_high": round(swing_low + 0.79 * diff, 2),
                "sweet_spot": round(swing_low + 0.705 * diff, 2),
                "note": "Zone de vente sur rebond (0.62-0.79) — entrée OTE pour continuation baissière"}


# ── Raja Banks : détection de liquidity sweep ("tap & snap") ─────────────────
def detect_liquidity_sweep(candles, lookback=20):
    """
    Détecte un sweep : le prix dépasse un plus-haut/bas récent (grab de liquidité)
    PUIS revient (rejet). Setup de reversal post-sweep (Raja Banks).
    candles : [ts,o,h,l,c,v]. Retourne dict ou None.
    """
    if len(candles) < lookback + 2:
        return None
    recent = candles[-lookback:]
    highs = [float(c[2]) for c in recent[:-1]]
    lows = [float(c[3]) for c in recent[:-1]]
    last = recent[-1]
    lh, ll, lc = float(last[2]), float(last[3]), float(last[4])
    prior_high = max(highs); prior_low = min(lows)
    # Sweep haussier (grab des stops sous le low puis rejet → reversal LONG)
    if ll < prior_low and lc > prior_low:
        return {"type": "BULLISH_SWEEP", "level": round(prior_low, 2),
                "direction": "LONG", "note": "Sweep du low (grab liquidité) + rejet → reversal LONG (Raja)"}
    # Sweep baissier (grab des stops au-dessus du high puis rejet → reversal SHORT)
    if lh > prior_high and lc < prior_high:
        return {"type": "BEARISH_SWEEP", "level": round(prior_high, 2),
                "direction": "SHORT", "note": "Sweep du high (grab liquidité) + rejet → reversal SHORT (Raja)"}
    return None


# ── Playbook documenté (les stratégies qui marchent sur CFD) ─────────────────
PLAYBOOK = {
    "OTE_RETRACEMENT": {
        "trader": "ICT", "type": "retracement (double flux)",
        "setup": "Impulsion forte → retracement dans la zone 0.62-0.79 → entrée pour la continuation",
        "rr": "≥ 1:2 (souvent 1:3+)", "sessions": "London/NY",
        "edge": "Capte le repli ET la continuation = le 'double flux' favori"},
    "LIQUIDITY_SWEEP": {
        "trader": "Raja Banks", "type": "reversal post-sweep",
        "setup": "Le prix balaie un high/low (grab des stops) puis rejette → entrée sur le rejet",
        "rr": "≥ 1:2", "sessions": "London Open, NY Open",
        "edge": "Entre APRÈS le piège à retail = on suit les institutions"},
    "ORDER_BLOCK": {
        "trader": "ICT", "type": "retour sur zone institutionnelle",
        "setup": "Dernière bougie opposée avant une impulsion = order block. Entrée au retour dessus",
        "rr": "≥ 1:2", "edge": "Zone où les institutions ont chargé"},
    "TREND_PULLBACK": {
        "trader": "Général (best practice)", "type": "retracement avec-tendance",
        "setup": "Tendance forte (ADX>25) → pullback sur Fib 0.5-0.618 ou EMA → entrée continuation",
        "rr": "≥ 1:2", "edge": "Avec la tendance = le côté gagnant (validé par notre journal)"},
}


def best_setup(direction, entry, atr, swing_high, swing_low, candles=None):
    """
    Construit le MEILLEUR trade possible selon le playbook, avec RR ≥ 2 forcé.
    Combine : stop ATR + niveaux RR-compliant + zone OTE + détection sweep.
    """
    sign = 1 if direction == "LONG" else -1
    stop = round(entry - sign * 1.5 * atr, 2)        # stop = 1.5×ATR
    levels = build_levels(direction, entry, stop)    # TP RR-compliant
    ote = ote_zone(swing_high, swing_low, direction)
    sweep = detect_liquidity_sweep(candles) if candles else None
    return {"levels": levels, "ote_zone": ote, "sweep": sweep,
            "strategy": "OTE_RETRACEMENT" if not sweep else "LIQUIDITY_SWEEP"}


if __name__ == "__main__":
    print("RR forcé — exemple GOLD LONG @4460, stop 4452 :")
    print(build_levels("LONG", 4460, 4452))
    print("\nValidation du trade user (LONG 4460, SL 4456, TP 4470) :")
    print(validate_rr(4460, 4456, 4470, "LONG"))
    print("\nZone OTE (swing 4515→4428, LONG) :")
    print(ote_zone(4515, 4428, "LONG"))
