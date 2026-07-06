#!/usr/bin/env python3
"""
NEWS RADAR, Détecteur de news temps réel multi-sources (ton bouclier fondamental)
══════════════════════════════════════════════════════════════════
Agrège en continu : GDELT (géopolitique) + Finnhub (news/calendrier) +
Marketaux (news+sentiment) + Fear&Greed + StockTwits. Score chaque news par
impact marché (sens GOLD & S&P, fiabilité), détecte la tendance de fond, et
alerte : "FENÊTRE PROPRE" vs "NE PAS TRADER (news incertaine)".

Rôle : Sam scalpe les micro-rebonds ; le Radar dit si le CONTEXTE les confirme.
Niveau gratuit. Marketaux = clé gratuite (MARKETAUX_API_KEY dans .env).
"""

import urllib.request, urllib.parse, json, os, time, datetime, re

ENV = "/Users/sam/trading/.env"


def _key(name):
    v = os.environ.get(name)
    if v:
        return v.strip()
    try:
        for line in open(ENV):
            if line.strip().startswith(name):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return None


def _get(url, timeout=10):
    req = urllib.request.Request(url, headers={"User-Agent": "news-radar/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "ignore"))


# ── Scoring d'impact (keyword → poids + sens GOLD/S&P) ──────────────────────
# Sens : +1 = haussier actif, -1 = baissier actif (pour chaque actif)
IMPACT = {
    "fomc":        (10, "depends", "depends"),
    "rate cut":    (9, +1, +1), "rate hike": (9, -1, -1),
    "powell":      (8, "depends", "depends"), "federal reserve": (7, "depends", "depends"),
    "cpi":         (9, "depends", "depends"), "inflation": (8, "depends", "depends"),
    "pce":         (7, "depends", "depends"), "ppi": (6, "depends", "depends"),
    "nonfarm":     (9, "depends", "depends"), "payroll": (9, "depends", "depends"),
    "jobless":     (4, "depends", "depends"), "unemployment": (6, "depends", "depends"),
    "recession":   (8, +1, -1),               # récession = refuge or↑, actions↓
    "war":         (8, +1, -1), "airstrike": (8, +1, -1), "missile": (7, +1, -1),
    "ceasefire":   (6, -1, +1), "peace deal": (6, -1, +1),
    "sanction":    (6, +1, -1), "tariff": (7, -1, -1), "trade war": (7, +1, -1),
    "credit":      (8, +1, -1), "default": (9, +1, -1), "bankruptcy": (7, +1, -1),
    "earnings":    (6, 0, +1), "guidance": (5, 0, +1),
    "dollar":      (6, "inv", 0), "treasury": (6, "depends", "depends"),
    "gold":        (5, "direct", 0), "crash": (8, +1, -1), "selloff": (7, +1, -1),
}

UNCERTAIN = ["could", "may", "reportedly", "rumor", "unconfirmed", "denies",
             "sources say", "weighing", "considering", "talks", "mixed", "uncertain"]


def score_item(headline):
    """Retourne {weight, gold, spx, uncertain} pour une manchette."""
    h = (headline or "").lower()
    weight = 0; gold = 0; spx = 0; hits = []
    for kw, (w, g, s) in IMPACT.items():
        if kw in h:
            weight = max(weight, w); hits.append(kw)
            for tgt, val in (("gold", g), ("spx", s)):
                if val in (1, -1):
                    if tgt == "gold": gold += val
                    else: spx += val
    uncertain = any(u in h for u in UNCERTAIN)
    return {"weight": weight, "gold": gold, "spx": spx,
            "uncertain": uncertain, "keywords": hits[:4]}


# ── Sources ─────────────────────────────────────────────────────────────────
def fetch_gdelt(query="(inflation OR \"federal reserve\" OR recession OR war OR gold OR \"stock market\")"):
    """GDELT, événements mondiaux temps quasi-réel (gratuit, sans clé)."""
    try:
        q = urllib.parse.quote(query)
        url = (f"https://api.gdeltproject.org/api/v2/doc/doc?query={q}"
               f"&mode=artlist&format=json&maxrecords=25&timespan=1d&sort=datedesc")
        d = _get(url)
        out = []
        for a in d.get("articles", [])[:25]:
            out.append({"headline": a.get("title", ""), "source": a.get("domain", "gdelt"),
                        "url": a.get("url", ""), "time": a.get("seendate", ""), "src": "GDELT"})
        return out
    except Exception:
        return []


def fetch_finnhub():
    try:
        import news_feed
        items = news_feed.fetch_market_news(limit=20)
        return [{"headline": i.get("headline", ""), "source": i.get("source", "finnhub"),
                 "url": i.get("url", ""), "time": f"{i.get('hours_ago','?')}h", "src": "Finnhub"}
                for i in items if isinstance(i, dict) and "headline" in i]
    except Exception:
        return []


def fetch_marketaux():
    key = _key("MARKETAUX_API_KEY")
    if not key:
        return []
    try:
        url = (f"https://api.marketaux.com/v1/news/all?language=en&filter_entities=true"
               f"&limit=25&api_token={key}")
        d = _get(url)
        out = []
        for a in d.get("data", [])[:25]:
            out.append({"headline": a.get("title", ""), "source": a.get("source", "marketaux"),
                        "url": a.get("url", ""), "time": a.get("published_at", ""), "src": "Marketaux",
                        "sentiment": a.get("entities", [{}])[0].get("sentiment_score") if a.get("entities") else None})
        return out
    except Exception:
        return []


def fetch_feargreed():
    """Fear & Greed Index (CNN, actions), psychologie du marché."""
    try:
        d = _get("https://production.dataviz.cnn.io/index/fearandgreed/graphdata")
        fg = d.get("fear_and_greed", {})
        return {"score": round(fg.get("score", 0)), "rating": fg.get("rating", "?")}
    except Exception:
        try:
            d = _get("https://api.alternative.me/fng/")
            v = d["data"][0]
            return {"score": int(v["value"]), "rating": v["value_classification"], "note": "(crypto F&G)"}
        except Exception:
            return None


# ── Radar : agrège, score, classe ──────────────────────────────────────────
def radar():
    items = []
    for fn in (fetch_gdelt, fetch_finnhub, fetch_marketaux):
        items += fn()

    # Calendrier macro structuré (consensus vs actual), fenêtres pré/post event
    try:
        import calendar_feed
        macro_cal = calendar_feed.event_mode()
    except Exception:
        macro_cal = {"mode": None, "detail": "calendar_feed indisponible"}
    # Dédup par titre
    seen, uniq = set(), []
    for it in items:
        k = (it.get("headline") or "")[:60].lower()
        if k and k not in seen:
            seen.add(k); uniq.append(it)
    # Score
    scored = []
    for it in uniq:
        sc = score_item(it["headline"])
        if sc["weight"] >= 4:    # garde l'impactant
            it.update(sc)
            scored.append(it)
    scored.sort(key=lambda x: x["weight"], reverse=True)

    fg = fetch_feargreed()

    # Tendance de fond : agrège le sens net sur les news impactantes
    gold_net = sum(i["gold"] for i in scored)
    spx_net = sum(i["spx"] for i in scored)
    uncertain_count = sum(1 for i in scored if i["uncertain"])

    return {"items": scored[:20], "fear_greed": fg,
            "gold_bias": gold_net, "spx_bias": spx_net,
            "uncertain_count": uncertain_count,
            "macro_calendar": macro_cal,
            "ts": datetime.datetime.now().isoformat()}


def _window_alert(r):
    """FENÊTRE PROPRE vs NE PAS TRADER selon la clarté du flux."""
    # Fenêtre pré-event : chiffre high-impact US imminent → veto absolu
    # (le 🔴 déclenche le veto majeur de prime_strategy)
    cal = r.get("macro_calendar") or {}
    if cal.get("mode") == "PRE_EVENT":
        return ("🔴 PRÉ-EVENT", f"Chiffre high-impact US imminent: {cal.get('detail')}, pas de nouveau trade")
    unc = r["uncertain_count"]; n = len(r["items"])
    if n == 0:
        return ("⚪ CALME", "Peu de news impactantes, contexte neutre")
    if unc >= max(3, n * 0.4):
        return ("🔴 NE PAS TRADER", f"{unc} news incertaines/contradictoires, risque de faux mouvement")
    suffix = ""
    if cal.get("mode") == "EVENT_DAY":
        suffix = f" · EVENT DAY ({cal.get('detail')})"
    if abs(r["gold_bias"]) >= 3 or abs(r["spx_bias"]) >= 3:
        return ("🟢 FENÊTRE CLAIRE", "Flux news directionnel net, contexte exploitable" + suffix)
    return ("🟡 PRUDENCE", "Flux mitigé, attendre confirmation" + suffix)


if __name__ == "__main__":
    r = radar()
    alert, msg = _window_alert(r)
    print(f"\n{'='*64}\n  📡 NEWS RADAR, {datetime.datetime.now().strftime('%H:%M:%S')}\n{'='*64}")
    print(f"  {alert}, {msg}")
    fg = r["fear_greed"]
    if fg:
        print(f"  😱 Fear & Greed : {fg['score']}/100 ({fg['rating']})")
    print(f"  Biais news → GOLD {r['gold_bias']:+d} · S&P {r['spx_bias']:+d}  | incertaines: {r['uncertain_count']}")
    print(f"\n  🔴 NEWS IMPACTANTES (top {len(r['items'])}) :")
    for it in r["items"]:
        flag = "⚠️" if it["uncertain"] else "  "
        g = f"or{it['gold']:+d}" if it['gold'] else ""
        s = f"spx{it['spx']:+d}" if it['spx'] else ""
        print(f"   {flag}[{it['weight']:>2}|{it['src']:8}] {it['headline'][:72]}  {g} {s}")
