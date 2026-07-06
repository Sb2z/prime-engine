#!/usr/bin/env python3
"""
AURUM, Moteur d'étude d'événements GOLD (XAUUSD)
══════════════════════════════════════════════════════════════════
Signes OR (≠ actions) : refuge → géo escalade = HAUSSIER ; taux réels↑ = baissier ;
Fed dovish = haussier ; USD fort = baissier.
Score surprise → réaction historique projetée + what-if.
"""
import datetime
import tz

# beta = % move OR par unité de surprise (signe = réaction OR)
EVENT_REACTIONS = {
    "FOMC": {"weight": 10, "window": "0→4-12h", "hit_rate": 0.75, "follow": 0.55,
             "scenarios": {"dovish": (+1.8, "Taux réels↓ = rally or"),
                           "hawkish": (-2.0, "Higher-for-longer = pression or"),
                           "neutral": (-0.2, "Vendu sur le fait")},
             "note": "Catalyseur #1 or via taux réels. Le dot plot domine."},
    "CPI_US": {"weight": 9, "beta": -4.0, "unit": "% MoM surprise", "window": "0→2-6h",
               "hit_rate": 0.62, "follow": 0.45,
               "tiers": [(0.3, 1.2, "choc"), (0.2, 0.8, "fort"), (0.1, 0.4, "modéré"), (0.0, 0.15, "léger")],
               "note": "PARADOXE OR : inflation chaude = Fed hawkish = taux réels↑ = baissier or (court terme). Froide = dovish = haussier."},
    "PCE": {"weight": 7, "beta": -3.0, "unit": "% surprise", "window": "2-4h", "hit_rate": 0.6, "follow": 0.4,
            "tiers": [(0.2, 0.7, "fort"), (0.1, 0.35, "modéré"), (0.0, 0.12, "léger")],
            "note": "Mesure Fed favorite. Même logique que CPI pour l'or."},
    "NFP": {"weight": 9, "beta": -0.005, "unit": "k surprise", "window": "0→3-6h", "hit_rate": 0.60, "follow": 0.45,
            "tiers": [(200, 1.4, "choc"), (100, 0.8, "fort"), (50, 0.4, "modéré"), (0, 0.15, "léger")],
            "note": "Emploi fort = USD↑ + taux↑ = baissier or. Faible = refuge/cut hopes = haussier or (asymétrie inversée vs actions)."},
    "PPI": {"weight": 6, "beta": -2.0, "unit": "% surprise", "window": "1-3h", "hit_rate": 0.55, "follow": 0.4,
            "tiers": [(0.3, 0.5, "fort"), (0.1, 0.25, "modéré"), (0.0, 0.1, "léger")],
            "note": "Préfigure CPI."},
    "ISM_SVC": {"weight": 6, "beta": -0.06, "unit": "pts vs forecast", "window": "1-3h", "hit_rate": 0.55, "follow": 0.4,
                "tiers": [(4, 0.5, "fort"), (2, 0.25, "modéré"), (0, 0.1, "léger")],
                "note": "Économie forte = baissier or (risk-on + taux). Faible = refuge."},
    "GDP_US": {"weight": 6, "beta": -0.10, "unit": "% surprise", "window": "2-4h", "hit_rate": 0.55, "follow": 0.4,
               "tiers": [(1.0, 0.5, "fort"), (0.3, 0.25, "modéré"), (0.0, 0.1, "léger")],
               "note": "PIB fort = baissier or. PIB faible = récession = refuge or."},
    "JOBLESS": {"weight": 4, "beta": 0.003, "unit": "k surprise", "window": "30m-1h", "hit_rate": 0.52, "follow": 0.35,
                "tiers": [(40, 0.4, "fort"), (15, 0.2, "modéré"), (0, 0.05, "léger")],
                "note": "Chômage↑ = dovish = haussier or léger."},
    "FED_SPEAK": {"weight": 6, "window": "1-3h", "hit_rate": 0.6, "follow": 0.4,
                  "scenarios": {"dovish": (+0.8, "Support or"), "hawkish": (-0.9, "Pression or"), "neutral": (0.0, "Neutre")},
                  "note": "Powell > gouverneurs. Écouter taux réels."},
    "GEO": {"weight": 8, "window": "1-72h", "hit_rate": 0.72, "follow": 0.6,
            "scenarios": {"escalation": (+2.5, "REFUGE = rally or instantané (≠ actions)"),
                          "deescalation": (-1.5, "Apaisement = sortie de l'or")},
            "note": "L'or est LE refuge. Escalade = haussier fort (inverse des actions)."},
    "CB_BUY": {"weight": 7, "window": "jours", "hit_rate": 0.7, "follow": 0.6,
               "scenarios": {"buying": (+1.0, "Banques centrales achètent = support structurel")},
               "note": "PBOC/BC asiatiques. Support de fond de l'or."},
    "USD_SHOCK": {"weight": 8, "window": "0→jours", "hit_rate": 0.75, "follow": 0.55,
                  "scenarios": {"dollar_up": (-1.2, "USD fort = baissier or (corrélation inverse #1)"),
                                "dollar_down": (+1.2, "USD faible = haussier or")},
                  "note": "DXY = corrélation inverse #1 de l'or."},
}

_TONE_KW = {
    "deescalation": ["ceasefire", "truce", "peace deal", "de-escalat", "deescalat", "agreement", "framework deal"],
    "escalation": ["airstrike", "missile", "attack", "war", "offensive", "strikes", "invasion", "conflict", "downed", "sanction"],
    "hot": ["largest", "rises", "accelerat", "hotter", "jump", "surge", "higher than", "above forecast", "sticky", "hot", "three years"],
    "cold": ["cools", "eases", "slows", "falls", "below forecast", "lower than", "softer", "weak", "decline", "drops"],
    "hawkish": ["higher for longer", "hawkish", "restrictive", "hold rates", "no rush", "patient", "against cut"],
    "dovish": ["rate cut", "rate cuts", "dovish", "easing", "pivot", "cut rates", "ready to cut"],
    "cb_buy": ["central bank", "pboc", "reserves", "bullion buying", "gold reserves"],
}


def map_event_name(name):
    n = (name or "").lower()
    if "cpi" in n or ("inflation" in n and "core" in n): return "CPI_US"
    if "pce" in n: return "PCE"
    if "ppi" in n or "producer price" in n: return "PPI"
    if "nonfarm" in n or "payroll" in n: return "NFP"
    if "ism" in n and ("service" in n or "non-man" in n): return "ISM_SVC"
    if "gdp" in n: return "GDP_US"
    if "jobless" in n or "initial claims" in n: return "JOBLESS"
    if "fomc" in n: return "FOMC"
    if "fed" in n or "powell" in n: return "FED_SPEAK"
    return None


def to_paris(ts):
    try:
        return tz.to_paris(datetime.datetime.strptime(ts[:16], "%Y-%m-%d %H:%M")).strftime("%m-%d %H:%M")
    except Exception:
        return ts[5:16]


def score_surprise(event_type, actual, forecast, prev=None):
    db = EVENT_REACTIONS.get(event_type)
    if not db or actual is None or forecast is None or "beta" not in db:
        return None
    try:
        surprise = float(actual) - float(forecast)
    except Exception:
        return None
    raw = db["beta"] * surprise
    direction = "LONG" if raw > 0 else ("SHORT" if raw < 0 else "NEUTRAL")
    label, tier = "léger", 0.1
    for thr, mag, lbl in db.get("tiers", []):
        if abs(surprise) >= thr:
            label, tier = lbl, mag; break
    expected = round(min(abs(raw), tier * 1.5), 2)
    return {"event": event_type, "surprise": round(surprise, 3), "unit": db.get("unit"),
            "direction": direction, "magnitude_pct": expected,
            "range": f"{round(expected*0.5,2)}% à {round(expected*1.5,2)}%", "window": db.get("window"),
            "hit_rate": db.get("hit_rate"), "weight": db.get("weight"), "note": db.get("note")}


def project_qualitative(event_type, tone):
    db = EVENT_REACTIONS.get(event_type)
    if not db or "scenarios" not in db or tone not in db["scenarios"]:
        return None
    mag, desc = db["scenarios"][tone]
    return {"event": event_type, "tone": tone, "direction": "LONG" if mag > 0 else ("SHORT" if mag < 0 else "NEUTRAL"),
            "magnitude_pct": abs(mag), "window": db.get("window"), "hit_rate": db.get("hit_rate"),
            "weight": db.get("weight"), "desc": desc, "note": db.get("note")}


def analyze_calendar_surprises():
    try:
        import news_feed
        cal = news_feed.fetch_economic_calendar()
    except Exception:
        return [], []
    today = datetime.date.today().isoformat()
    NOISE = ["2nd est", "3rd est", "final", "continuing", " yoy", "qoq", "revision",
             "chicago", "dallas", "richmond", "philadelphia", "empire", "kansas"]
    released, upcoming = [], []
    for e in cal:
        nm = (e.get("event") or "").lower()
        if any(w in nm for w in NOISE):
            continue
        et = map_event_name(e.get("event"))
        if not et:
            continue
        t = e.get("time") or ""
        actual, est, prev = e.get("actual"), e.get("estimate"), e.get("prev")
        if actual not in (None, "") and est not in (None, ""):
            pr = score_surprise(et, actual, est, prev)
            if pr:
                pr["name"] = e.get("event"); pr["time"] = t
                released.append(pr)
        elif t[:10] >= today and est not in (None, ""):
            upcoming.append({"name": e.get("event"), "type": et, "time": t, "estimate": est,
                             "prev": prev, "weight": EVENT_REACTIONS.get(et, {}).get("weight", 0)})
    released.sort(key=lambda x: x.get("time", ""), reverse=True)
    upcoming.sort(key=lambda x: (-x["weight"], x["time"]))
    return released[:8], upcoming[:8]


if __name__ == "__main__":
    print("CPI +0.2 chaud →", score_surprise("CPI_US", 0.4, 0.2))
    print("Géo escalade →", project_qualitative("GEO", "escalation"))
    rel, up = analyze_calendar_surprises()
    print("\nSurprises:", [(r["name"], r["direction"], r["magnitude_pct"]) for r in rel[:4]])
    print("À venir:", [(u["name"], u["weight"]) for u in up[:4]])
