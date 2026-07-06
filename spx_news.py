#!/usr/bin/env python3
"""
SENTINEL-500, Couche News S&P 500
Base de réactions ACTIONS + classification auto du ton + flux live (Finnhub).
Score positif = bullish S&P, négatif = bearish.

Logique régime actuel "good is bad / bad is good" (Fed anti-inflation) :
  données chaudes → Fed hawkish → baissier actions ; données froides → dovish → haussier.
  MAIS données trop faibles → peur récession → baissier (noté).
"""

import datetime

try:
    import news_feed
    _HAS_LIVE = True
except Exception:
    _HAS_LIVE = False

# ── Base de réactions S&P (signes ACTIONS) ──────────────────────────────────
NEWS_IMPACT_DB = {
    "FOMC":       {"impact": "CRITICAL", "hawkish": -2.0, "dovish": +2.5, "neutral": -0.2,
                   "note": "Décision Fed = catalyseur #1 actions. Dovish = rally, hawkish = sell-off."},
    "FED_SPEAK":  {"impact": "HIGH", "hawkish": -1.0, "dovish": +1.2, "neutral": 0.0,
                   "note": "Membres Fed. 'higher for longer' = bearish, 'cut possible' = bullish."},
    "CPI_US":     {"impact": "CRITICAL", "hot": -1.5, "cold": +1.5,
                   "note": "Inflation chaude = Fed restrictive = bearish actions. Froide = bullish."},
    "PCE":        {"impact": "HIGH", "hot": -1.0, "cold": +1.0,
                   "note": "Mesure favorite Fed. Même logique que CPI."},
    "PPI":        {"impact": "MED", "hot": -0.5, "cold": +0.5, "note": "Préfigure CPI."},
    "NFP":        {"impact": "CRITICAL", "strong": -0.6, "weak": +0.2,
                   "note": "Régime good-is-bad : emploi fort = rate fears = bearish. Faible modéré = cut hopes. TROP faible = récession = bearish."},
    "JOBLESS":    {"impact": "LOW", "rising": +0.2, "falling": -0.2,
                   "note": "Inscriptions chômage ↑ = marché travail se détend = dovish léger."},
    "ADP":        {"impact": "MED", "strong": -0.4, "weak": +0.3, "note": "Préfigure NFP."},
    "GDP_US":     {"impact": "HIGH", "above": +0.4, "below": -0.6,
                   "note": "Croissance = bon pour earnings (sauf si surchauffe → rate fears)."},
    "ISM":        {"impact": "HIGH", "above": +0.5, "below": -0.5,
                   "note": "PMI > 50 = expansion = bullish ; < 50 = contraction = bearish."},
    "RETAIL":     {"impact": "MED", "strong": +0.4, "weak": -0.5, "note": "Conso US = moteur 70% PIB."},
    "CONSUMER":   {"impact": "MED", "strong": +0.3, "weak": -0.3, "note": "Confiance conso."},
    "EARNINGS":   {"impact": "HIGH", "beat": +1.5, "miss": -1.5,
                   "note": "Saison résultats. Beats larges = rally, miss = correction."},
    "GEO_ESCALATION":   {"impact": "HIGH", "score": -1.5,
                         "note": "Conflit = risk-off = baissier actions (INVERSE de l'or)."},
    "GEO_DEESCALATION": {"impact": "MED", "score": +1.0,
                         "note": "Apaisement = risk-on = haussier actions."},
    "CREDIT_STRESS":    {"impact": "CRITICAL", "score": -2.0,
                         "note": "Spreads crédit qui s'écartent = stress systémique = sell-off."},
    "TARIFF":     {"impact": "HIGH", "score": -1.0, "note": "Guerre commerciale = incertitude = bearish."},
}

_TONE_KW = {
    "deescalation": ["ceasefire", "truce", "peace deal", "de-escalat", "deescalat", "agreement", "framework deal", "diplomacy"],
    "escalation":   ["airstrike", "missile", "attack", "war", "offensive", "strikes", "invasion", "conflict", "downed"],
    "hot":          ["largest", "rises", "accelerat", "hotter", "jump", "surge", "higher than", "above forecast", "sticky", "hot", "three years", "beats", "stronger"],
    "cold":         ["cools", "eases", "slows", "falls", "below forecast", "lower than", "softer", "weak", "misses", "decline", "drops"],
    "hawkish":      ["higher for longer", "hawkish", "restrictive", "hold rates", "no rush", "patient", "against cut", "delay cut", "premature"],
    "dovish":       ["rate cut", "rate cuts", "dovish", "easing", "pivot", "cut rates", "ready to cut"],
    "beat":         ["beat", "beats", "tops estimates", "record profit", "strong earnings", "raises guidance"],
    "miss":         ["miss", "misses", "disappoints", "cuts guidance", "profit warning", "weak earnings"],
}


def _count(h):
    h = h.lower()
    return {k: sum(1 for w in ws if w in h) for k, ws in _TONE_KW.items()}


def _classify_tone(headline, tags):
    f = _count(headline)
    if "GEO_ESCALATION" in tags or "GEO_DEESCALATION" in tags:
        if f["deescalation"] > f["escalation"]:
            return ("GEO_DEESCALATION", "deescalation")
        if f["escalation"] > 0:
            return ("GEO_ESCALATION", "escalation")
    if "CPI_US" in tags or "PCE" in tags or "PPI" in tags:
        evt = "PCE" if "PCE" in tags else ("PPI" if "PPI" in tags else "CPI_US")
        return (evt, "hot" if f["hot"] >= f["cold"] else "cold")
    if "FED_SPEAK" in tags or "FOMC" in tags:
        evt = "FOMC" if "FOMC" in tags else "FED_SPEAK"
        if f["hawkish"] > f["dovish"]:
            return (evt, "hawkish")
        if f["dovish"] > 0:
            return (evt, "dovish")
        return (evt, "neutral")
    if "NFP" in tags:
        return ("NFP", "strong" if f["hot"] >= f["cold"] else "weak")
    # Earnings detectables par mots
    if f["beat"] or f["miss"]:
        return ("EARNINGS", "beat" if f["beat"] >= f["miss"] else "miss")
    return (None, None)


def assess_news_sentiment(active_events):
    total, breakdown = 0.0, []
    for ev in active_events:
        db = NEWS_IMPACT_DB.get(ev.get("type", "").upper())
        if not db:
            continue
        tone = ev.get("tone", "neutral")
        score = db.get(tone, db.get("score", 0.0))
        decay = max(0.1, 1.0 - ev.get("hours_ago", 0) / 12)
        sd = round(score * decay, 2)
        total += sd
        breakdown.append({"event": ev["type"], "tone": tone, "score": sd, "note": db.get("note", "")})
    direction = "LONG" if total >= 0.5 else ("SHORT" if total <= -0.5 else "NEUTRAL")
    return {"total_score": round(total, 2), "direction": direction, "breakdown": breakdown}


def get_live_news_context():
    if not _HAS_LIVE:
        return None
    try:
        news = news_feed.fetch_market_news(limit=25)
    except Exception:
        return None
    if not news or (isinstance(news[0], dict) and news[0].get("error")):
        return None

    seen, active = set(), []
    infl_tone = fed_tone = None
    for it in news:
        evt, tone = _classify_tone(it.get("headline", ""), it.get("tags", []))
        if not evt:
            continue
        key = (evt, tone)
        if key in seen:
            continue
        seen.add(key)
        active.append({"type": evt, "tone": tone, "hours_ago": it.get("hours_ago", 0),
                       "description": it.get("headline", "")[:110], "confidence": "LIVE"})
        if evt in ("CPI_US", "PCE", "PPI") and infl_tone is None:
            infl_tone = tone
        if evt in ("FED_SPEAK", "FOMC") and fed_tone is None:
            fed_tone = tone

    # Biais fondamental dérivé (pour ACTIONS)
    if infl_tone == "cold" or fed_tone == "dovish":
        posture, note, lt = "DOVISH_SUPPORT", "Inflation en baisse / Fed dovish → soutien actions.", "BULL"
    elif infl_tone == "hot" or fed_tone == "hawkish":
        posture, note, lt = "HAWKISH_RISK", "Inflation chaude / Fed prudente → pression valorisations.", "BEAR_RISK"
    else:
        posture, note, lt = "NEUTRAL", "Pas de signal inflation/Fed dominant en live.", "NEUTRAL"

    upcoming = []
    try:
        cal = news_feed.fetch_economic_calendar()
        today = datetime.date.today().isoformat()
        kw = ["pce", "cpi", "payroll", "nonfarm", "fomc", "gdp", "ism", "jolts",
              "powell", "fed ", "retail sales", "consumer", "jobless", "ppi"]
        for e in cal:
            t = (e.get("time") or "")
            nm = (e.get("event") or "").lower()
            if t[:10] >= today and any(k in nm for k in kw):
                high = any(k in nm for k in ["pce", "cpi", "payroll", "nonfarm", "fomc", "powell"])
                upcoming.append({"event": e.get("event"), "time": t[11:16], "date": t[:10],
                                 "estimate": e.get("estimate"), "prev": e.get("prev"),
                                 "gold_impact": "HIGH" if high else "MED", "note": "Live Finnhub"})
        upcoming = sorted(upcoming, key=lambda x: (x["date"], x["time"]))[:6]
    except Exception:
        pass

    return {"source": "LIVE (Finnhub)", "active_events": active, "upcoming_high_impact": upcoming,
            "fundamental_bias": {"fed_posture": posture, "rate_cut_probability": "dérivé live",
                                 "note": note, "spx_long_term": lt}}


def get_current_news_context():
    live = get_live_news_context()
    if live and live["active_events"]:
        return live
    return {"source": "FALLBACK", "active_events": [], "upcoming_high_impact": [],
            "fundamental_bias": {"fed_posture": "NEUTRAL", "rate_cut_probability": "?",
                                 "note": "Flux live indisponible.", "spx_long_term": "NEUTRAL"}}


def news_score_for_spx():
    ctx = get_current_news_context()
    sent = assess_news_sentiment(ctx["active_events"])
    fed = ctx["fundamental_bias"].get("fed_posture", "")
    bonus = +0.5 if "DOVISH" in fed else (-0.5 if "HAWKISH" in fed else 0.0)
    total = round(sent["total_score"] + bonus, 2)
    direction = "LONG" if total >= 0.5 else ("SHORT" if total <= -0.5 else "NEUTRAL")
    return {"score": total, "direction": direction, "sentiment": sent,
            "context": ctx, "fundamental_bonus": bonus}


if __name__ == "__main__":
    r = news_score_for_spx()
    print(f"\n📰 SENTINEL-500 News, score {r['score']:+.2f} {r['direction']}")
    print(f"  Posture Fed : {r['context']['fundamental_bias']['fed_posture']}  (bonus {r['fundamental_bonus']:+.2f})")
    for ev in r["sentiment"]["breakdown"]:
        mk = "🟢" if ev["score"] > 0 else ("🔴" if ev["score"] < 0 else "⚪")
        print(f"  {mk} {ev['event']:18} {ev['tone']:13} {ev['score']:+.2f}")
    print("\n  À venir :")
    for e in r["context"]["upcoming_high_impact"]:
        print(f"   ⏰ {e['date']} {e['time']} {e['event']} [{e['gold_impact']}]")
