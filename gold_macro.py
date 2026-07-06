#!/usr/bin/env python3
"""
Gold AI, Couche Macro : DXY, taux réels, corrélations, régime macro
Fetch via TradingView WebSocket (mêmes symboles, zéro rate-limit)
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tv_live    import TVLiveClient
from tv_candles import TVCandleClient

# ── Actifs macro corrélés à l'or ─────────────────────────────────────────────
# DXY  : corrélation inverse forte (~-0.85)  → DXY ↑ = GOLD ↓
# US10Y: corrélation inverse modérée        → yields ↑ = GOLD ↓  (taux réels)
# SILVER: corrélation positive forte (~+0.9) → silver ↑ = GOLD ↑ (confirmation)
# VIX  : corrélation positive modérée       → peur ↑ = GOLD ↑ (refuge)
# SPX  : corrélation variable               → risk-off = GOLD ↑
# OIL  : corrélation faible/positive         → inflation ↑ = GOLD ↑

MACRO_SYMBOLS_LIVE = [
    "TVC:DXY",          # Dollar Index
    "TVC:SILVER",       # Argent (confirmation or)
    "TVC:US10Y",        # Taux 10 ans US (proxy taux réels)
    "TVC:VIX",          # Volatilité = peur
    "CAPITALCOM:US500", # S&P500
    "TVC:USOIL",        # Pétrole (inflation)
]

MACRO_SYMBOLS_TA = ["DXY", "SILVER", "US10Y"]

MACRO_SYMBOL_MAP_CANDLES = {
    "DXY":    "TVC:DXY",
    "SILVER": "TVC:SILVER",
    "US10Y":  "TVC:US10Y",
}

# ── Seuils de corrélation historiques GOLD ────────────────────────────────────
# Basés sur données 2020-2025, affinés par régime macro
CORRELATION_THRESHOLDS = {
    "DXY": {
        "strong_bull_gold":  {"dxy_chg": -0.5, "signal": "LONG", "weight": 2.5},
        "bull_gold":         {"dxy_chg": -0.2, "signal": "LONG", "weight": 1.5},
        "neutral":           {"dxy_chg":  0.2, "signal": "NEUTRAL", "weight": 0},
        "bear_gold":         {"dxy_chg":  0.5, "signal": "SHORT", "weight": -1.5},
        "strong_bear_gold":  {"dxy_chg":  1.0, "signal": "SHORT", "weight": -2.5},
    },
    "US10Y": {
        "bull_gold":   {"yield_chg": -0.05, "signal": "LONG",  "weight": 1.5},
        "neutral":     {"yield_chg":  0.02, "signal": "NEUTRAL", "weight": 0},
        "bear_gold":   {"yield_chg":  0.05, "signal": "SHORT", "weight": -1.5},
    },
    "SILVER": {
        "confirm_long":  {"silver_chg":  0.5, "signal": "LONG",  "weight": 1.0},
        "confirm_short": {"silver_chg": -0.5, "signal": "SHORT", "weight": -1.0},
    },
    "VIX": {
        "fear_spike":  {"vix": 25, "signal": "LONG",  "weight": 1.5},  # refuge
        "elevated":    {"vix": 20, "signal": "LONG",  "weight": 0.8},
        "low":         {"vix": 15, "signal": "SHORT", "weight": -0.5}, # risk-on
    }
}

# ── Réactions historiques GOLD aux événements macro (base de connaissance) ──
# Format: événement → impact moyen, direction, magnitude, durée
MACRO_REACTIONS = {
    "CPI_HOT":          {"direction": "LONG",  "magnitude": "+0.8%", "duration": "2-4h",
                         "note": "Inflation↑ → or refuge, MAIS si hawkish Fed → SHORT"},
    "CPI_COLD":         {"direction": "SHORT", "magnitude": "-0.5%", "duration": "1-2h",
                         "note": "Désinflation → baisse or, taux réels remontent"},
    "NFP_STRONG":       {"direction": "SHORT", "magnitude": "-0.6%", "duration": "2-3h",
                         "note": "Emploi fort → Fed hawkish → taux↑ → or↓"},
    "NFP_WEAK":         {"direction": "LONG",  "magnitude": "+0.7%", "duration": "2-4h",
                         "note": "Emploi faible → Fed dovish → taux↓ → or↑"},
    "FOMC_HAWKISH":     {"direction": "SHORT", "magnitude": "-1.2%", "duration": "4-8h",
                         "note": "Hausse taux ou ton hawkish = très bearish or"},
    "FOMC_DOVISH":      {"direction": "LONG",  "magnitude": "+1.5%", "duration": "4-12h",
                         "note": "Pause/baisse taux = très bullish or"},
    "GEOPOLITICAL":     {"direction": "LONG",  "magnitude": "+1-3%", "duration": "1-48h",
                         "note": "Choc géopolitique → fuite vers or (refuge)"},
    "DXY_BREAKDOWN":    {"direction": "LONG",  "magnitude": "+0.8%", "duration": "4-8h",
                         "note": "Cassure DXY sous support → mécanisme inverse"},
    "RISK_OFF_GLOBAL":  {"direction": "LONG",  "magnitude": "+1.0%", "duration": "2-6h",
                         "note": "VIX spike + équités -1% → or refuge"},
    "RISK_ON_REBOUND":  {"direction": "SHORT", "magnitude": "-0.5%", "duration": "2-4h",
                         "note": "Rebond équités + VIX baisse → rotation hors or"},
    "GDP_MISS":         {"direction": "LONG",  "magnitude": "+0.4%", "duration": "1-3h",
                         "note": "Croissance faible → Fed accommodant → or↑"},
    "FED_SPEAKER_HAWK": {"direction": "SHORT", "magnitude": "-0.3%", "duration": "1-2h",
                         "note": "Discours hawkish Fed → dollar↑ → or↓"},
}

# ── Calendrier économique, prochains événements impactants (à mettre à jour) ─
# Ces données doivent être rafraîchies quotidiennement
UPCOMING_EVENTS = [
    # Format: {"date": "2026-05-28", "time": "14:30", "event": "...", "impact": "HIGH/MED/LOW", "prev": "...", "forecast": "..."}
    {"date": "2026-05-28", "time": "14:30", "event": "US GDP Q1 Final", "impact": "HIGH",
     "prev": "2.4%", "forecast": "2.4%", "note": "Révision PIB US Q1"},
    {"date": "2026-05-28", "time": "14:30", "event": "US Jobless Claims", "impact": "MED",
     "prev": "227K", "forecast": "225K", "note": "Chômage hebdo"},
    {"date": "2026-05-30", "time": "14:30", "event": "US PCE Inflation", "impact": "HIGH",
     "prev": "2.3%", "forecast": "2.2%", "note": "Inflation préférée Fed = clé or"},
]


def fetch_macro_data() -> dict:
    """
    Fetch T0 des actifs macro via WebSocket TradingView.
    Retourne un dict complet avec prix, variations, signaux.
    """
    results = {}

    try:
        raw = TVLiveClient(symbols=MACRO_SYMBOLS_LIVE, timeout=14).fetch()
        sym_map = {
            "DXY":    ("DXY",    raw.get("DXY", {})),
            "SILVER": ("SILVER", raw.get("SILVER", {})),
            "US10Y":  ("US10Y",  raw.get("US10Y", {})),
            "VIX":    ("VIX",    raw.get("VIX", {})),
            "US500":  ("US500",  raw.get("US500", {})),
            "USOIL":  ("OIL",    raw.get("USOIL", {})),
        }

        for key, (name, d) in sym_map.items():
            lp  = d.get("lp")
            chp = d.get("chp", 0) or 0
            results[name] = {
                "price": lp,
                "chg":   chp,
                "raw":   d,
            }
    except Exception as e:
        results["error"] = str(e)

    return results


def score_macro_confluence(macro: dict) -> dict:
    """
    Analyse macro et produit un score de confluence pour GOLD.
    Score positif = bullish GOLD, négatif = bearish GOLD.
    Retourne: score total, détail des signaux, direction.
    """
    signals = []
    total_score = 0.0

    dxy_d    = macro.get("DXY", {})
    silver_d = macro.get("SILVER", {})
    us10y_d  = macro.get("US10Y", {})
    vix_d    = macro.get("VIX", {})
    us500_d  = macro.get("US500", {})

    # ── Signal DXY ────────────────────────────────────────────────────────────
    dxy_chg = dxy_d.get("chg", 0) or 0
    if dxy_chg <= -0.5:
        s, w = "LONG", 2.5
        signals.append(("DXY", f"DXY {dxy_chg:+.2f}% forte baisse → LONG GOLD fort", w))
    elif dxy_chg <= -0.2:
        s, w = "LONG", 1.5
        signals.append(("DXY", f"DXY {dxy_chg:+.2f}% baisse → LONG GOLD", w))
    elif dxy_chg >= 1.0:
        s, w = "SHORT", -2.5
        signals.append(("DXY", f"DXY {dxy_chg:+.2f}% forte hausse → SHORT GOLD fort", w))
    elif dxy_chg >= 0.5:
        s, w = "SHORT", -1.5
        signals.append(("DXY", f"DXY {dxy_chg:+.2f}% hausse → SHORT GOLD", w))
    else:
        signals.append(("DXY", f"DXY {dxy_chg:+.2f}% neutre", 0.0))
        w = 0.0
    total_score += w if 'w' in dir() else 0

    # ── Signal SILVER (confirmation) ──────────────────────────────────────────
    silver_chg = silver_d.get("chg", 0) or 0
    if silver_chg >= 0.5:
        w = 1.0
        signals.append(("SILVER", f"Silver {silver_chg:+.2f}% ↑ confirme LONG GOLD", w))
    elif silver_chg <= -0.5:
        w = -1.0
        signals.append(("SILVER", f"Silver {silver_chg:+.2f}% ↓ confirme SHORT GOLD", w))
    else:
        w = 0.0
        signals.append(("SILVER", f"Silver {silver_chg:+.2f}% neutre", w))
    total_score += w

    # ── Signal US10Y (taux) ───────────────────────────────────────────────────
    us10y_chg = us10y_d.get("chg", 0) or 0
    if us10y_chg <= -0.5:
        w = 1.5
        signals.append(("US10Y", f"Taux 10Y {us10y_chg:+.2f}% baisse → LONG GOLD", w))
    elif us10y_chg >= 0.5:
        w = -1.5
        signals.append(("US10Y", f"Taux 10Y {us10y_chg:+.2f}% hausse → SHORT GOLD", w))
    else:
        w = 0.0
        signals.append(("US10Y", f"Taux 10Y {us10y_chg:+.2f}% neutre", w))
    total_score += w

    # ── Signal VIX (risk-off/on) ──────────────────────────────────────────────
    vix_price = vix_d.get("price") or 0
    vix_chg   = vix_d.get("chg", 0) or 0
    if vix_price >= 25 or vix_chg >= 5:
        w = 1.5
        signals.append(("VIX", f"VIX={vix_price:.1f} ({vix_chg:+.1f}%) spike peur → refuge GOLD", w))
    elif vix_price >= 20:
        w = 0.8
        signals.append(("VIX", f"VIX={vix_price:.1f} élevé → GOLD refuge", w))
    elif vix_price <= 15 and vix_chg <= -2:
        w = -0.5
        signals.append(("VIX", f"VIX={vix_price:.1f} bas risk-on → GOLD sous pression", w))
    else:
        w = 0.0
        signals.append(("VIX", f"VIX={vix_price:.1f} ({vix_chg:+.1f}%) neutre", w))
    total_score += w

    # ── Signal US500 (risk-off/on) ────────────────────────────────────────────
    us500_chg = us500_d.get("chg", 0) or 0
    if us500_chg <= -1.0:
        w = 1.2
        signals.append(("US500", f"S&P {us500_chg:+.2f}% chute → risk-off → GOLD ↑", w))
    elif us500_chg >= 1.0:
        w = -0.8
        signals.append(("US500", f"S&P {us500_chg:+.2f}% hausse → risk-on → GOLD ↓", w))
    else:
        w = 0.0
        signals.append(("US500", f"S&P {us500_chg:+.2f}% neutre", w))
    total_score += w

    # ── Direction finale ──────────────────────────────────────────────────────
    direction = "LONG" if total_score >= 1.0 else ("SHORT" if total_score <= -1.0 else "NEUTRAL")

    return {
        "score":     round(total_score, 2),
        "direction": direction,
        "signals":   signals,
        "macro":     macro,
    }


def get_upcoming_events() -> list:
    """
    Prochains événements macro impactants pour GOLD.
    Essaie le calendrier temps réel (Finnhub) d'abord, sinon fallback codé en dur.
    """
    import datetime
    now = datetime.datetime.now()

    # ── Flux temps réel prioritaire ──
    try:
        import news_feed
        cal = news_feed.fetch_economic_calendar()
        if cal:
            today = datetime.date.today().isoformat()
            kw = ["pce", "cpi", "payroll", "nonfarm", "fomc", "gdp", "inflation",
                  "fed ", "ism", "jolts", "powell", "jobless", "retail sales", "ppi"]
            live = []
            for e in cal:
                t = (e.get("time") or "")
                name = (e.get("event") or "")
                nl = name.lower()
                if len(t) < 16 or t[:10] < today:
                    continue
                if not any(k in nl for k in kw):
                    continue
                try:
                    ev_dt = datetime.datetime.strptime(t[:16], "%Y-%m-%d %H:%M")
                except Exception:
                    continue
                hours_away = (ev_dt - now).total_seconds() / 3600
                if -1 < hours_away < 72:
                    high = any(k in nl for k in ["pce", "cpi", "payroll", "nonfarm", "fomc", "powell"])
                    live.append({
                        "date": t[:10], "time": t[11:16], "event": name,
                        "impact": "HIGH" if high else "MED",
                        "forecast": e.get("estimate"), "prev": e.get("prev"),
                        "note": "Données temps réel Finnhub",
                        "hours_away": round(hours_away, 1),
                    })
            if live:
                return sorted(live, key=lambda x: x["hours_away"])[:8]
    except Exception:
        pass

    # ── Fallback codé en dur ──
    upcoming = []
    for ev in UPCOMING_EVENTS:
        try:
            ev_dt = datetime.datetime.strptime(f"{ev['date']} {ev['time']}", "%Y-%m-%d %H:%M")
            hours_away = (ev_dt - now).total_seconds() / 3600
            if -1 < hours_away < 48:
                ev_copy = ev.copy()
                ev_copy["hours_away"] = round(hours_away, 1)
                upcoming.append(ev_copy)
        except:
            pass
    return sorted(upcoming, key=lambda x: x.get("hours_away", 99))


def macro_regime(macro: dict) -> str:
    """
    Détermine le régime macro pour l'or en une phrase.
    """
    dxy_chg   = macro.get("DXY",    {}).get("chg", 0) or 0
    vix_p     = macro.get("VIX",    {}).get("price") or 0
    us500_chg = macro.get("US500",  {}).get("chg", 0) or 0
    us10y_chg = macro.get("US10Y",  {}).get("chg", 0) or 0

    if dxy_chg <= -0.3 and us10y_chg <= 0:
        return "GOLDILOCKS_BULL"  # DXY baisse + taux stables = idéal LONG GOLD
    if vix_p >= 25 and us500_chg <= -1:
        return "RISK_OFF_EXTREME"  # Panique marché = refuge GOLD fort
    if dxy_chg >= 0.5 and us10y_chg >= 0.3:
        return "RATE_HIKE_FEAR"  # Taux montent + dollar fort = bearish GOLD
    if us500_chg >= 1.0 and vix_p <= 15:
        return "RISK_ON_BULL"  # Euphorie = rotation hors GOLD
    if abs(dxy_chg) < 0.2 and abs(us10y_chg) < 0.2:
        return "CONSOLIDATION"  # Rien ne bouge = range GOLD
    return "MIXED"


# ── Test direct ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n📊 Fetch macro data...\n")
    macro = fetch_macro_data()
    for k, v in macro.items():
        if isinstance(v, dict) and "price" in v:
            print(f"  {k:8} ${v['price']:.4f}  {v['chg']:+.2f}%")

    print("\n🧮 Score macro confluence GOLD :")
    result = score_macro_confluence(macro)
    print(f"  Score: {result['score']:+.2f}  Direction: {result['direction']}")
    print("  Signaux détaillés :")
    for src, msg, w in result["signals"]:
        marker = "✅" if w > 0 else ("❌" if w < 0 else "⚪")
        print(f"    {marker} [{src:6}] {msg}  (poids: {w:+.1f})")

    print(f"\n  Régime: {macro_regime(macro)}")

    print("\n📅 Événements macro à venir :")
    for ev in get_upcoming_events():
        print(f"  ⏰ {ev['time']} ({ev['hours_away']:+.1f}h), {ev['event']} [{ev['impact']}], {ev['note']}")
