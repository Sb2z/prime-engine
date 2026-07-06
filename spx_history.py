#!/usr/bin/env python3
"""
SENTINEL-500, Moteur d'étude d'événements (Event-Reaction Engine)
══════════════════════════════════════════════════════════════════
Quand une annonce tombe :
  1. score la SURPRISE (actual vs forecast vs prev)
  2. regarde la RÉACTION HISTORIQUE du S&P à ce type + cette ampleur
  3. PROJETTE l'impact probable (direction, magnitude %, fenêtre, taux de réussite)
  4. peut MESURER la réaction réelle sur les bougies (étude ex-post)

Base : bêtas et statistiques documentés des réactions S&P 500 aux macro-events.
"""

import datetime
import tz

# ── Base de réactions quantifiée ────────────────────────────────────────────
# Pour chaque événement :
#   beta       : % move S&P attendu PAR UNITÉ de surprise (signe = sens actions)
#   unit       : unité de la surprise (l'écart actual-forecast)
#   tiers      : (seuil_surprise_abs, magnitude%, label), ampleurs typiques
#   window     : durée de la réaction dominante
#   hit_rate   : % de fois où le sens de la réaction tient (historique)
#   follow     : tendance de continuation (>0.5 = le move continue, <0.5 = fade)
#   weight     : envergure systémique 0-10 (poids de l'événement)
EVENT_REACTIONS = {
    "FOMC": {
        "weight": 10, "window": "instantané → 4-12h", "hit_rate": 0.78, "follow": 0.55,
        "scenarios": {
            "dovish":  (+1.8, "Rally, pivot/baisse anticipée. Ex: pumps de +1 à +3%."),
            "hawkish": (-2.2, "Sell-off, higher for longer. Ex: -1 à -3%."),
            "neutral": (-0.2, "Léger fade si rien de neuf (vendu sur le fait)."),
        },
        "note": "Catalyseur #1. Le dot plot et le ton Powell dominent."},
    "CPI_US": {
        "weight": 9, "beta": -7.0, "unit": "% MoM surprise", "window": "instantané → 2-6h",
        "hit_rate": 0.72, "follow": 0.5,
        "tiers": [(0.3, 1.5, "choc"), (0.2, 1.0, "fort"), (0.1, 0.5, "modéré"), (0.0, 0.2, "léger")],
        "note": "Surprise chaude (+) = -S&P (Fed hawkish). Froide (-) = +S&P. Le plus market-moving des data."},
    "PCE": {
        "weight": 7, "beta": -5.0, "unit": "% surprise", "window": "2-4h", "hit_rate": 0.65, "follow": 0.45,
        "tiers": [(0.2, 0.8, "fort"), (0.1, 0.4, "modéré"), (0.0, 0.15, "léger")],
        "note": "Mesure favorite Fed. Même sens que CPI, impact un cran sous."},
    "NFP": {
        "weight": 9, "beta": -0.004, "unit": "k surprise (emplois)", "window": "instantané → 3-6h",
        "hit_rate": 0.60, "follow": 0.45,
        "tiers": [(200, 1.2, "choc"), (100, 0.7, "fort"), (50, 0.4, "modéré"), (0, 0.15, "léger")],
        "note": "Régime good-is-bad : emploi très fort = rate fears = -S&P. Faible modéré = +S&P (cut hopes). TROP faible = récession = -S&P (asymétrie)."},
    "PPI": {
        "weight": 6, "beta": -3.0, "unit": "% surprise", "window": "1-3h", "hit_rate": 0.58, "follow": 0.4,
        "tiers": [(0.3, 0.6, "fort"), (0.1, 0.3, "modéré"), (0.0, 0.1, "léger")],
        "note": "Préfigure CPI. Impact moindre mais confirme la tendance inflation."},
    "ISM_MFG": {
        "weight": 7, "beta": 0.12, "unit": "pts vs forecast", "window": "1-3h", "hit_rate": 0.62, "follow": 0.5,
        "tiers": [(4, 0.8, "fort"), (2, 0.4, "modéré"), (0, 0.15, "léger")],
        "note": "PMI manufacturier. >50 expansion. Le franchissement de 50 est clé (sentiment cyclique)."},
    "ISM_SVC": {
        "weight": 8, "beta": 0.14, "unit": "pts vs forecast", "window": "1-3h", "hit_rate": 0.64, "follow": 0.5,
        "tiers": [(4, 0.9, "fort"), (2, 0.5, "modéré"), (0, 0.15, "léger")],
        "note": "PMI services = 70% de l'économie US. Plus impactant que le manufacturier."},
    "RETAIL": {
        "weight": 6, "beta": 0.25, "unit": "% MoM surprise", "window": "1-2h", "hit_rate": 0.58, "follow": 0.45,
        "tiers": [(1.0, 0.7, "fort"), (0.4, 0.35, "modéré"), (0.0, 0.1, "léger")],
        "note": "Conso US. Forte = +S&P (earnings) sauf si stoke les taux."},
    "GDP_US": {
        "weight": 6, "beta": 0.15, "unit": "% surprise (annualisé)", "window": "2-4h", "hit_rate": 0.55, "follow": 0.4,
        "tiers": [(1.0, 0.6, "fort"), (0.3, 0.3, "modéré"), (0.0, 0.1, "léger")],
        "note": "Croissance = earnings. Mais souvent déjà price (donnée retardée)."},
    "JOBLESS": {
        "weight": 4, "beta": -0.002, "unit": "k surprise", "window": "30m-1h", "hit_rate": 0.52, "follow": 0.35,
        "tiers": [(40, 0.4, "fort"), (15, 0.2, "modéré"), (0, 0.05, "léger")],
        "note": "Hebdo. Hausse = marché travail se détend = dovish léger (+S&P modéré)."},
    "FED_SPEAK": {
        "weight": 6, "window": "1-3h", "hit_rate": 0.6, "follow": 0.4,
        "scenarios": {"dovish": (+0.6, "Soutien"), "hawkish": (-0.7, "Pression"), "neutral": (0.0, "Neutre")},
        "note": "Membres Fed. Powell > gouverneurs > présidents régionaux."},
    "EARNINGS": {
        "weight": 7, "window": "instantané (titre) → jours (indice)", "hit_rate": 0.6, "follow": 0.55,
        "scenarios": {"beat": (+0.8, "Beats larges (megacaps) tirent l'indice"),
                      "miss": (-1.0, "Miss megacap = pression indice"), "neutral": (0.0, "Conforme")},
        "note": "Saison earnings. Megacaps (AAPL/NVDA/MSFT) = poids démesuré sur le S&P."},
    "GEO": {
        "weight": 6, "window": "1-72h", "hit_rate": 0.65, "follow": 0.5,
        "scenarios": {"escalation": (-1.0, "Risk-off = -S&P (inverse de l'or)"),
                      "deescalation": (+0.7, "Apaisement = risk-on")},
        "note": "Géopolitique = risk-off pour actions. Magnitude selon ampleur."},
    "CREDIT_STRESS": {
        "weight": 9, "window": "jours", "hit_rate": 0.8, "follow": 0.6,
        "scenarios": {"widening": (-2.0, "Spreads ↑ = stress systémique = sell-off")},
        "note": "Le signal de stress le plus fiable. Spreads HY = canari."},
}


def score_surprise(event_type, actual, forecast, prev=None):
    """
    Score la surprise d'une donnée chiffrée et projette l'impact S&P.
    Retourne dict {surprise, magnitude_pct, direction, range, hit_rate, follow, label, note}.
    """
    db = EVENT_REACTIONS.get(event_type)
    if not db or actual is None or forecast is None:
        return None
    try:
        surprise = float(actual) - float(forecast)
    except Exception:
        return None

    beta = db.get("beta")
    if beta is None:
        return None  # événement qualitatif (utiliser project_qualitative)

    raw_move = beta * surprise
    direction = "LONG" if raw_move > 0 else ("SHORT" if raw_move < 0 else "NEUTRAL")

    # Ampleur via les tiers (sur |surprise|)
    label, tier_mag = "léger", 0.1
    for thr, mag, lbl in db.get("tiers", []):
        if abs(surprise) >= thr:
            label, tier_mag = lbl, mag
            break
    expected = round(min(abs(raw_move), tier_mag * 1.5), 2)
    lo = round(expected * 0.5, 2); hi = round(expected * 1.5, 2)

    return {
        "event": event_type, "surprise": round(surprise, 3), "unit": db.get("unit"),
        "direction": direction, "magnitude_pct": expected,
        "range": f"{lo:.2f}% à {hi:.2f}%", "window": db.get("window"),
        "hit_rate": db.get("hit_rate"), "follow": db.get("follow"),
        "label": label, "weight": db.get("weight"), "note": db.get("note"),
    }


def project_qualitative(event_type, tone):
    """Projette l'impact d'un événement qualitatif (FOMC/Fed speak/géo/earnings) selon le ton."""
    db = EVENT_REACTIONS.get(event_type)
    if not db or "scenarios" not in db:
        return None
    sc = db["scenarios"].get(tone)
    if not sc:
        return None
    mag, desc = sc
    return {
        "event": event_type, "tone": tone,
        "direction": "LONG" if mag > 0 else ("SHORT" if mag < 0 else "NEUTRAL"),
        "magnitude_pct": abs(mag), "window": db.get("window"),
        "hit_rate": db.get("hit_rate"), "follow": db.get("follow"),
        "weight": db.get("weight"), "desc": desc, "note": db.get("note"),
    }


# ── Mapping nom Finnhub → type d'événement ──────────────────────────────────
def to_paris(ts_str):
    """Convertit un timestamp calendrier UTC 'YYYY-MM-DD HH:MM:SS' → 'MM-DD HH:MM' Paris (UTC+2)."""
    try:
        dt = tz.to_paris(datetime.datetime.strptime(ts_str[:16], "%Y-%m-%d %H:%M"))
        return dt.strftime("%m-%d %H:%M")
    except Exception:
        return ts_str[5:16]


def map_event_name(name):
    n = (name or "").lower()
    if "cpi" in n or ("inflation" in n and "core" in n): return "CPI_US"
    if "pce" in n: return "PCE"
    if "ppi" in n or "producer price" in n: return "PPI"
    if "nonfarm" in n or "payroll" in n: return "NFP"
    if "ism" in n and ("service" in n or "non-man" in n): return "ISM_SVC"
    if "ism" in n or "pmi" in n: return "ISM_MFG"
    if "retail sales" in n: return "RETAIL"
    if "gdp" in n: return "GDP_US"
    if "jobless" in n or "initial claims" in n: return "JOBLESS"
    if "fomc" in n: return "FOMC"
    if "fed" in n or "powell" in n: return "FED_SPEAK"
    return None


def analyze_calendar_surprises():
    """
    Récupère le calendrier live, score les SURPRISES des données déjà publiées (actual présent),
    et projette l'impact S&P de chacune. Retourne (released[], upcoming[]).
    """
    try:
        import news_feed
        cal = news_feed.fetch_economic_calendar()
    except Exception:
        return [], []
    today = datetime.date.today().isoformat()
    # Filtre le bruit : révisions, sous-composantes, régionaux
    NOISE = ["2nd est", "3rd est", "final", "continuing", " yoy", "qoq", "revision",
             "chicago", "dallas", "richmond", "philadelphia", "empire", "kansas"]
    released, upcoming = [], []
    for e in cal:
        nm_low = (e.get("event") or "").lower()
        if any(w in nm_low for w in NOISE):
            continue
        etype = map_event_name(e.get("event"))
        if not etype:
            continue
        t = e.get("time") or ""
        actual, est, prev = e.get("actual"), e.get("estimate"), e.get("prev")
        if actual not in (None, "") and est not in (None, ""):
            proj = score_surprise(etype, actual, est, prev)
            if proj:
                proj["name"] = e.get("event"); proj["time"] = t
                proj["actual"] = actual; proj["estimate"] = est
                released.append(proj)
        elif t[:10] >= today and est not in (None, ""):
            upcoming.append({"name": e.get("event"), "type": etype, "time": t,
                             "estimate": est, "prev": prev,
                             "weight": EVENT_REACTIONS.get(etype, {}).get("weight", 0)})
    released.sort(key=lambda x: x.get("time", ""), reverse=True)
    upcoming.sort(key=lambda x: (-x["weight"], x["time"]))
    return released[:8], upcoming[:8]


def measure_reaction(symbol_candles, event_ts_iso, bars_after=8):
    """
    Étude ex-post : mesure la réaction RÉELLE du S&P sur les bougies autour d'un event.
    symbol_candles : liste [ts, o, h, l, c, v] (ts en secondes). event_ts_iso : ISO.
    Retourne le move % sur N bougies après l'événement.
    """
    try:
        ev = datetime.datetime.fromisoformat(event_ts_iso).timestamp()
    except Exception:
        return None
    before = [c for c in symbol_candles if c[0] <= ev]
    after = [c for c in symbol_candles if c[0] > ev]
    if not before or len(after) < 1:
        return None
    ref = float(before[-1][4])
    window = after[:bars_after]
    end = float(window[-1][4])
    hi = max(float(c[2]) for c in window); lo = min(float(c[3]) for c in window)
    return {
        "ref_price": round(ref, 2), "move_pct": round((end - ref) / ref * 100, 2),
        "max_up_pct": round((hi - ref) / ref * 100, 2),
        "max_down_pct": round((lo - ref) / ref * 100, 2),
        "bars": len(window),
    }


if __name__ == "__main__":
    print("═══ TEST : surprise CPI +0.2% vs forecast ═══")
    print(score_surprise("CPI_US", actual=0.4, forecast=0.2))
    print("\n═══ TEST : FOMC hawkish ═══")
    print(project_qualitative("FOMC", "hawkish"))
    print("\n═══ CALENDRIER LIVE, surprises + à venir ═══")
    rel, up = analyze_calendar_surprises()
    print(f"Publiés récents ({len(rel)}):")
    for r in rel[:5]:
        print(f"  {r['time']} {r['name']}: surprise {r['surprise']:+} → S&P {r['direction']} ~{r['magnitude_pct']}% ({r['range']}), hit {r['hit_rate']*100:.0f}%")
    print(f"À venir ({len(up)}):")
    for u in up[:5]:
        print(f"  {u['time']} {u['name']} [poids {u['weight']}] est={u['estimate']} prev={u['prev']}")
