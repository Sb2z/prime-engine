#!/usr/bin/env python3
"""
Gold AI — Couche News : calendrier économique, sentiment, catalyseurs
Flux temps réel via news_feed.py (Finnhub) + fallback codé en dur.
"""

import json, datetime, time

# Flux live optionnel — ne casse jamais si indisponible
try:
    import news_feed
    _HAS_LIVE = True
except Exception:
    _HAS_LIVE = False

# ── Base de connaissance : impact des nouvelles sur GOLD ─────────────────────
# Enrichie à chaque trade — apprentissage continu
NEWS_IMPACT_DB = {
    # ─── Banques centrales ────────────────────────────────────────────────────
    "FOMC":       {"impact": "CRITICAL", "delay": "0h",  "duration": "4-12h",
                   "hawkish": -2.0, "dovish": +2.5, "neutral": -0.3,
                   "note": "Événement le plus impactant pour GOLD. Réaction instantanée sur le dot plot."},
    "FED_SPEAK":  {"impact": "HIGH",     "delay": "0h",  "duration": "1-3h",
                   "hawkish": -1.0, "dovish": +1.2, "neutral": 0.0,
                   "note": "Powell/membres Fed. Écouter 'higher for longer' vs 'cut possible'."},
    "ECB":        {"impact": "MED",      "delay": "0h",  "duration": "1-2h",
                   "hawkish": -0.5, "dovish": +0.7, "neutral": 0.0,
                   "note": "Indirect via EUR/USD → DXY → GOLD"},
    "BOJ":        {"impact": "MED",      "delay": "0h",  "duration": "1-4h",
                   "hawkish": +0.3, "dovish": -0.3, "neutral": 0.0,
                   "note": "Hausse BOJ = JPY fort = risk-off = GOLD ↑ souvent"},

    # ─── Inflation ────────────────────────────────────────────────────────────
    "CPI_US":     {"impact": "CRITICAL", "delay": "0h",  "duration": "2-6h",
                   "hot": -0.5, "cold": +1.2,
                   "note": "Paradoxe : inflation↑ = bearish GOLD si Fed hausse. Cold CPI = dovish = bullish."},
    "PCE":        {"impact": "HIGH",     "delay": "0h",  "duration": "2-4h",
                   "hot": -0.4, "cold": +1.0,
                   "note": "Mesure favorite Fed. Même logique que CPI."},
    "PPI":        {"impact": "MED",      "delay": "15m", "duration": "1-2h",
                   "hot": -0.2, "cold": +0.5,
                   "note": "Préfigure CPI, impact moindre."},

    # ─── Emploi ───────────────────────────────────────────────────────────────
    "NFP":        {"impact": "CRITICAL", "delay": "0h",  "duration": "3-6h",
                   "strong": -1.0, "weak": +1.5,
                   "note": "NFP fort → Fed hawkish → GOLD ↓. NFP faible → récession fear → GOLD ↑"},
    "JOBLESS":    {"impact": "LOW",      "delay": "0h",  "duration": "30m",
                   "rising": +0.3, "falling": -0.2,
                   "note": "Chômage hebdo, impact limité sauf tendance."},
    "ADP":        {"impact": "MED",      "delay": "0h",  "duration": "1h",
                   "strong": -0.5, "weak": +0.7,
                   "note": "Préfigure NFP. Impact modéré."},

    # ─── Croissance ───────────────────────────────────────────────────────────
    "GDP_US":     {"impact": "HIGH",     "delay": "0h",  "duration": "2-4h",
                   "above": -0.4, "below": +0.8,
                   "note": "PIB faible = récession = refuge or."},
    "ISM":        {"impact": "MED",      "delay": "0h",  "duration": "1-2h",
                   "above": -0.3, "below": +0.5,
                   "note": "PMI manufacturier/services US."},

    # ─── Géopolitique ─────────────────────────────────────────────────────────
    "GEO_ESCALATION": {"impact": "CRITICAL", "delay": "0h", "duration": "1-72h",
                       "score": +3.0,
                       "note": "Conflit → refuge or instantané. Durée variable."},
    "GEO_DEESCALATION": {"impact": "HIGH",   "delay": "0h", "duration": "2-8h",
                         "score": -1.5,
                         "note": "Cessez-le-feu, accord → rotation hors or."},
    "SANCTIONS":   {"impact": "HIGH",  "delay": "0h", "duration": "24-48h",
                    "score": +1.5,
                    "note": "Sanctions → risk-off + défiance USD → or↑"},

    # ─── Chine ────────────────────────────────────────────────────────────────
    "CHINA_BUY":   {"impact": "HIGH",  "delay": "1-4h", "duration": "4-24h",
                    "score": +1.0,
                    "note": "PBOC/banques centrales asiatiques achètent GOLD → support fort"},
    "CHINA_DATA":  {"impact": "MED",   "delay": "0h",  "duration": "1-3h",
                    "strong": +0.3, "weak": -0.3,
                    "note": "Croissance Chine = demande GOLD physique."},
}

# ── Sentiment composite ───────────────────────────────────────────────────────
def assess_news_sentiment(active_events: list) -> dict:
    """
    Prend une liste d'événements actifs et calcule le score de sentiment GOLD.
    active_events: [{"type": "FOMC", "tone": "dovish", "hours_ago": 1}, ...]
    """
    total_score = 0.0
    breakdown   = []

    for ev in active_events:
        ev_type  = ev.get("type", "").upper()
        tone     = ev.get("tone", "neutral").lower()
        hours_ago = ev.get("hours_ago", 0)

        db = NEWS_IMPACT_DB.get(ev_type)
        if not db:
            continue

        # Score brut selon le ton
        score = 0.0
        if tone in db:
            score = db[tone]
        elif "score" in db:
            score = db["score"]

        # Decay temporel : impact diminue avec le temps
        decay = max(0.1, 1.0 - (hours_ago / 12))
        score_decayed = round(score * decay, 2)

        total_score += score_decayed
        breakdown.append({
            "event":   ev_type,
            "tone":    tone,
            "score":   score_decayed,
            "note":    db.get("note", ""),
        })

    direction = "LONG" if total_score >= 0.5 else ("SHORT" if total_score <= -0.5 else "NEUTRAL")

    return {
        "total_score": round(total_score, 2),
        "direction":   direction,
        "breakdown":   breakdown,
    }


# ── Classification automatique du ton d'une manchette ───────────────────────
_TONE_KEYWORDS = {
    "deescalation": ["ceasefire", "cease-fire", "truce", "peace deal", "peace talks",
                     "de-escalat", "deescalat", "agreement", "diplomacy", "framework deal",
                     "nuclear deal", "mou"],
    "escalation":   ["airstrike", "air strike", "missile", "attack", "offensive", "war",
                     "expand", "downed", "strikes", "invasion", "bombard", "conflict"],
    "hot":          ["largest", "rises", "rise", "accelerat", "hotter", "jump", "surge",
                     "higher than", "above forecast", "sticky", "hot", "soared", "climbs",
                     "biggest increase", "three years", "two years"],
    "cold":         ["cools", "cool", "eases", "ease", "slows", "slow", "falls", "fall",
                     "below forecast", "lower than", "softer", "soft", "decline", "drops"],
    "hawkish":      ["higher for longer", "hawkish", "restrictive", "hold rates", "no rush",
                     "patient", "against cut", "delay cut", "not yet", "premature", "caution"],
    "dovish":       ["rate cut", "rate cuts", "dovish", "easing", "pivot", "cut rates",
                     "ready to cut", "supports cut"],
}


def _classify_tone(headline: str, tags: list) -> tuple:
    """
    Retourne (event_type, tone) le plus pertinent pour une manchette.
    Réassigne GEO_ESCALATION → GEO_DEESCALATION si mots de paix présents.
    """
    h = headline.lower()
    found = {k: sum(1 for w in words if w in h) for k, words in _TONE_KEYWORDS.items()}

    # Géopolitique : choisir escalation vs deescalation selon le décompte
    if "GEO_ESCALATION" in tags or "GEO_DEESCALATION" in tags:
        if found["deescalation"] > found["escalation"]:
            return ("GEO_DEESCALATION", "deescalation")
        elif found["escalation"] > 0:
            return ("GEO_ESCALATION", "escalation")

    # Inflation : hot vs cold
    if "CPI_US" in tags or "PCE" in tags or "PPI" in tags:
        evt = "PCE" if "PCE" in tags else ("PPI" if "PPI" in tags else "CPI_US")
        if found["hot"] > found["cold"]:
            return (evt, "hot")
        elif found["cold"] > 0:
            return (evt, "cold")
        return (evt, "hot")  # "largest annual increase" etc. → défaut hot

    # Fed speak : hawkish vs dovish
    if "FED_SPEAK" in tags or "FOMC" in tags:
        evt = "FOMC" if "FOMC" in tags else "FED_SPEAK"
        if found["hawkish"] > found["dovish"]:
            return (evt, "hawkish")
        elif found["dovish"] > 0:
            return (evt, "dovish")
        return (evt, "neutral")

    if "SANCTIONS" in tags:
        return ("SANCTIONS", "score")
    if "CHINA_BUY" in tags:
        return ("CHINA_BUY", "score")
    if "NFP" in tags:
        return ("NFP", "weak" if found["cold"] else ("strong" if found["hot"] else "strong"))
    return (None, None)


def get_live_news_context() -> dict | None:
    """
    Construit le contexte news depuis le flux temps réel (Finnhub).
    Retourne None si indisponible → fallback codé en dur.
    """
    if not _HAS_LIVE:
        return None
    try:
        news = news_feed.fetch_market_news(limit=25)
    except Exception:
        return None
    if not news or (isinstance(news[0], dict) and news[0].get("error")):
        return None

    # 1) Active events : classer chaque manchette, dédupliquer par (type, tone)
    seen, active = set(), []
    inflation_tone = None   # pour dériver le biais fondamental
    fed_tone = None
    for item in news:
        evt, tone = _classify_tone(item.get("headline", ""), item.get("tags", []))
        if not evt:
            continue
        key = (evt, tone)
        if key in seen:
            continue
        seen.add(key)
        active.append({
            "type": evt, "tone": tone,
            "hours_ago": item.get("hours_ago", 0),
            "description": item.get("headline", "")[:110],
            "confidence": "LIVE",
        })
        if evt in ("CPI_US", "PCE", "PPI") and inflation_tone is None:
            inflation_tone = tone
        if evt in ("FED_SPEAK", "FOMC") and fed_tone is None:
            fed_tone = tone

    # 2) Biais fondamental DÉRIVÉ du live (plus de valeur codée en dur périmée)
    if inflation_tone == "hot" or fed_tone == "hawkish":
        fed_posture = "HAWKISH_RISK"
        note = "Inflation chaude / Fed prudente détectée en live → taux higher-for-longer = pression baissière GOLD."
        longterm = "BEAR_SHORT_TERM"
    elif inflation_tone == "cold" or fed_tone == "dovish":
        fed_posture = "DOVISH"
        note = "Inflation en baisse / Fed dovish détectée en live → support GOLD."
        longterm = "BULL"
    else:
        fed_posture = "NEUTRAL"
        note = "Pas de signal inflation/Fed dominant dans les news live."
        longterm = "NEUTRAL"

    # 3) Calendrier à venir (high-impact, gold-relevant, futur)
    upcoming = []
    try:
        cal = news_feed.fetch_economic_calendar()
        today = datetime.date.today().isoformat()
        kw = ["pce", "cpi", "payroll", "nonfarm", "fomc", "gdp", "inflation",
              "fed ", "ism", "jolts", "powell", "jobless"]
        for e in cal:
            t = (e.get("time") or "")
            name = (e.get("event") or "").lower()
            if t[:10] >= today and any(k in name for k in kw):
                upcoming.append({
                    "event": e.get("event"), "time": t[11:16], "date": t[:10],
                    "estimate": e.get("estimate"), "prev": e.get("prev"),
                    "gold_impact": "HIGH" if any(k in name for k in ["pce","cpi","payroll","nonfarm","fomc"]) else "MED",
                    "note": "Données temps réel Finnhub",
                })
        upcoming = sorted(upcoming, key=lambda x: (x["date"], x["time"]))[:6]
    except Exception:
        pass

    return {
        "source": "LIVE (Finnhub)",
        "active_events": active,
        "upcoming_high_impact": upcoming,
        "fundamental_bias": {
            "fed_posture": fed_posture,
            "rate_cut_probability": "dérivé du flux live",
            "note": note,
            "gold_long_term": longterm,
        },
    }


def get_current_news_context() -> dict:
    """
    Contexte news : essaie le flux temps réel d'abord, sinon fallback codé en dur.
    """
    live = get_live_news_context()
    if live and live["active_events"]:
        return live

    # ── FALLBACK codé en dur (si pas de clé API ou flux indisponible) ──
    current_context = {
        "source": "FALLBACK (codé en dur)",
        "active_events": [
            {
                "type": "GEO_ESCALATION",
                "tone": "escalation",
                "hours_ago": 8,
                "description": "Hausse OIL +3% = probable tension géopolitique Moyen-Orient/Iran",
                "confidence": "MEDIUM"
            },
        ],
        "upcoming_high_impact": [
            {"event": "US GDP Q1 Final", "time": "14:30", "date": "2026-05-28",
             "expected_direction": "NEUTRAL", "gold_impact": "MED",
             "note": "Révision. Si miss = LONG GOLD. Si beat = SHORT GOLD."},
            {"event": "PCE Core (inflation)", "time": "14:30", "date": "2026-05-30",
             "expected_direction": "COLD", "gold_impact": "HIGH",
             "note": "PCE prévu en baisse = bullish GOLD (Fed dovish)"},
        ],
        "fundamental_bias": {
            "fed_posture": "NEUTRAL_TO_DOVISH",
            "rate_cut_probability": "65% pour Sept 2026",
            "note": "Fed en mode attente. Données inflation décisives. Biais légèrement dovish = support GOLD.",
            "gold_long_term": "BULL",
        }
    }
    return current_context


def news_score_for_gold() -> dict:
    """
    Score news complet pour GOLD, combinant actifs et contexte fondamental.
    """
    context = get_current_news_context()
    sentiment = assess_news_sentiment(context["active_events"])

    # Biais fondamental
    fundamental_bonus = 0.0
    fed = context["fundamental_bias"].get("fed_posture", "")
    if "DOVISH" in fed:
        fundamental_bonus = +0.5
    elif "HAWKISH" in fed:
        fundamental_bonus = -0.5

    total = round(sentiment["total_score"] + fundamental_bonus, 2)
    direction = "LONG" if total >= 0.5 else ("SHORT" if total <= -0.5 else "NEUTRAL")

    return {
        "score":        total,
        "direction":    direction,
        "sentiment":    sentiment,
        "context":      context,
        "fundamental_bonus": fundamental_bonus,
    }


# ── Test direct ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n📰 Analyse news GOLD\n")
    result = news_score_for_gold()

    print(f"  Score news total : {result['score']:+.2f}")
    print(f"  Direction news   : {result['direction']}")
    print(f"  Bonus fondamental: {result['fundamental_bonus']:+.2f} ({result['context']['fundamental_bias']['fed_posture']})")

    print("\n  Événements actifs :")
    for ev in result["sentiment"]["breakdown"]:
        marker = "🟢" if ev["score"] > 0 else ("🔴" if ev["score"] < 0 else "⚪")
        print(f"    {marker} {ev['event']:20} tone={ev['tone']:12} score={ev['score']:+.2f}")
        print(f"       → {ev['note']}")

    print("\n  Prochains événements HIGH impact :")
    for ev in result["context"]["upcoming_high_impact"]:
        print(f"  ⏰ {ev['date']} {ev['time']} — {ev['event']} [{ev['gold_impact']}]")
        print(f"     → {ev['note']}")

    print(f"\n  Biais fondamental : {result['context']['fundamental_bias']['note']}")
