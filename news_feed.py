#!/usr/bin/env python3
"""
NEWS FEED TEMPS RÉEL, Finnhub (gratuit) + fallback
══════════════════════════════════════════════════════════════════
Branche le calendrier économique + les news marché en temps réel.

Clé API (gratuite, 60 req/min), l'une de ces 3 méthodes :
  1. Variable d'env : export FINNHUB_API_KEY=xxxxx
  2. Fichier        : /Users/sam/trading/.env       →  FINNHUB_API_KEY=xxxxx
  3. Fichier JSON   : /Users/sam/trading/api_keys.json → {"finnhub": "xxxxx"}

SANS clé → le module retombe proprement sur le calendrier codé en dur
de gold_macro/gold_news (aucune erreur). Le système continue de tourner.
"""

import os, json, urllib.request, urllib.parse, datetime, time

KEY_FILE_ENV  = "/Users/sam/trading/.env"
KEY_FILE_JSON = "/Users/sam/trading/api_keys.json"
CACHE_FILE    = "/Users/sam/trading/news_cache.json"
CACHE_TTL     = 600  # 10 min, respecte le quota gratuit

# Mots-clés → mapping vers la base de réaction NEWS_IMPACT_DB (macro + actions)
GOLD_KEYWORDS = {
    "fomc": "FOMC", "federal reserve": "FED_SPEAK", "powell": "FED_SPEAK",
    "rate cut": "FED_SPEAK", "rate hike": "FED_SPEAK", "interest rate": "FED_SPEAK",
    "fed ": "FED_SPEAK", "fed's": "FED_SPEAK",
    "cpi": "CPI_US", "inflation": "CPI_US", "pce": "PCE", "ppi": "PPI",
    "nonfarm": "NFP", "payroll": "NFP", "jobless": "JOBLESS", "unemployment": "NFP",
    "jobs report": "NFP", "labor market": "NFP", "adp": "ADP",
    "gdp": "GDP_US", "ism": "ISM", "pmi": "ISM", "ecb": "ECB", "boj": "BOJ",
    "retail sales": "RETAIL", "consumer confidence": "CONSUMER", "consumer sentiment": "CONSUMER",
    # Actions / S&P
    "s&p": "EQUITY", "sp500": "EQUITY", "s&p 500": "EQUITY", "wall street": "EQUITY",
    "stocks": "EQUITY", "equities": "EQUITY", "nasdaq": "EQUITY", "dow": "EQUITY",
    "earnings": "EARNINGS", "profit": "EARNINGS", "guidance": "EARNINGS", "results": "EARNINGS",
    "recession": "GEO_ESCALATION", "tariff": "TARIFF", "trade war": "TARIFF",
    "credit": "CREDIT_STRESS", "default": "CREDIT_STRESS",
    # Géopolitique (risk-off pour actions)
    "war": "GEO_ESCALATION", "missile": "GEO_ESCALATION", "strike": "GEO_ESCALATION",
    "conflict": "GEO_ESCALATION", "iran": "GEO_ESCALATION", "israel": "GEO_ESCALATION",
    "ceasefire": "GEO_DEESCALATION", "peace deal": "GEO_DEESCALATION",
    "sanction": "SANCTIONS",
}


def _load_key() -> str | None:
    k = os.environ.get("FINNHUB_API_KEY")
    if k:
        return k.strip()
    try:
        with open(KEY_FILE_ENV) as f:
            for line in f:
                if line.strip().startswith("FINNHUB_API_KEY"):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    try:
        with open(KEY_FILE_JSON) as f:
            return json.load(f).get("finnhub")
    except Exception:
        pass
    return None


def _get(url: str, timeout=10):
    req = urllib.request.Request(url, headers={"User-Agent": "trading-bot/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _cache_get():
    try:
        with open(CACHE_FILE) as f:
            c = json.load(f)
        if time.time() - c.get("ts", 0) < CACHE_TTL:
            return c.get("data")
    except Exception:
        pass
    return None


def _cache_put(data):
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump({"ts": time.time(), "data": data}, f)
    except Exception:
        pass


def fetch_market_news(limit=15) -> list:
    """News marché générales, scorées par pertinence GOLD."""
    key = _load_key()
    if not key:
        return []
    cached = _cache_get()
    if cached is not None:
        return cached
    try:
        url = f"https://finnhub.io/api/v1/news?category=general&token={key}"
        raw = _get(url)
    except Exception as e:
        return [{"error": str(e)}]

    scored = []
    now = time.time()
    for item in raw[:60]:
        headline = (item.get("headline") or "").lower()
        summary  = (item.get("summary") or "").lower()
        text = headline + " " + summary
        tags, direction = [], 0
        for kw, evt in GOLD_KEYWORDS.items():
            if kw in text:
                tags.append(evt)
        if not tags:
            continue
        age_h = (now - item.get("datetime", now)) / 3600
        if age_h > 24:
            continue
        scored.append({
            "headline": item.get("headline", "")[:120],
            "tags": list(set(tags)),
            "hours_ago": round(age_h, 1),
            "source": item.get("source", ""),
            "url": item.get("url", ""),
        })
    scored = scored[:limit]
    _cache_put(scored)
    return scored


def fetch_economic_calendar() -> list:
    """
    Calendrier économique temps réel. Endpoint premium sur Finnhub, si 403/erreur, retourne [] et le système utilise le calendrier codé en dur.
    """
    key = _load_key()
    if not key:
        return []
    try:
        url = f"https://finnhub.io/api/v1/calendar/economic?token={key}"
        raw = _get(url)
        events = raw.get("economicCalendar", []) if isinstance(raw, dict) else []
        out = []
        for e in events:
            if e.get("country") != "US":
                continue
            out.append({
                "event": e.get("event"),
                "time": e.get("time"),
                "actual": e.get("actual"),
                "estimate": e.get("estimate"),
                "prev": e.get("prev"),
                "impact": e.get("impact"),
            })
        return out
    except Exception:
        return []   # premium-only ou erreur → fallback silencieux


def status() -> dict:
    """État de la connexion news temps réel."""
    key = _load_key()
    if not key:
        return {"connected": False, "mode": "FALLBACK (calendrier codé en dur)",
                "reason": "aucune clé FINNHUB_API_KEY trouvée"}
    news = fetch_market_news()
    if news and isinstance(news[0], dict) and "error" in news[0]:
        return {"connected": False, "mode": "FALLBACK",
                "reason": f"clé présente mais erreur API: {news[0]['error']}"}
    cal = fetch_economic_calendar()
    return {
        "connected": True,
        "mode": "TEMPS RÉEL (Finnhub)",
        "news_gold_relevant": len(news),
        "calendar_available": len(cal) > 0,
        "calendar_note": "OK" if cal else "calendrier=premium → fallback codé en dur",
    }


if __name__ == "__main__":
    import sys
    st = status()
    print("═══ NEWS FEED, ÉTAT ═══")
    print(json.dumps(st, indent=2, ensure_ascii=False))
    if st["connected"]:
        print("\n═══ NEWS GOLD-PERTINENTES (24h) ═══")
        for n in fetch_market_news():
            print(f"  [{n['hours_ago']}h] {n['tags']}, {n['headline']}")
        cal = fetch_economic_calendar()
        if cal:
            print("\n═══ CALENDRIER ÉCO US (temps réel) ═══")
            for e in cal[:10]:
                print(f"  {e['time']} {e['event']} | act={e['actual']} est={e['estimate']} prev={e['prev']}")
