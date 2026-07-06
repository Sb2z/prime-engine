#!/usr/bin/env python3
"""CALENDAR FEED, calendrier macro structuré (consensus vs actual).

Source primaire : JSON hebdo public ForexFactory (ff_calendar_thisweek.json),
cache local 1h. ATTENTION : ce feed gratuit ne contient PAS la valeur "actual"
(vérifié le 10/06/2026, même les événements passés n'en portent pas).
L'enrichissement actual passe par l'API JBlanked si JBLANKED_API_KEY est dans
.env (clé gratuite, limitée → cache 1 jour) ; sinon surprise_z reste None et
seul le veto PRÉ-event fonctionne, ce qui est déjà l'essentiel du risque.

Expose :
  fetch_events()            événements normalisés {event,currency,impact,time_utc,forecast,previous,actual}
  pre_event_window()        événements high-impact USD dans les 30 prochaines minutes (veto)
  event_mode()              {"mode": PRE_EVENT|EVENT_DAY|None, ...} pour news_radar
  surprise_z(event)         (actual-forecast) / écart-type historique des surprises
                            de CET événement (historique constitué au fil de l'eau)
"""

import datetime as dt
import json
import os
import re
import statistics
import urllib.request

FF_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
CACHE_FILE = "/Users/sam/trading/calendar_cache.json"
HISTORY_FILE = "/Users/sam/trading/calendar_history.json"
ENV = "/Users/sam/trading/.env"

CACHE_TTL_S = 3600
FETCH_BACKOFF_S = 600  # après un échec (le feed FF rate-limite par IP), pas de retry avant 10 min
PRE_EVENT_MIN = 30          # veto nouveaux trades T-30min
EVENT_DAY_LOOKBACK_H = 8    # surprise forte dans les 8h → mode event day
EVENT_DAY_Z = 1.0
MIN_HISTORY_FOR_Z = 4       # observations minimum avant de calculer un z-score


def _env_key(name):
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


def _get_json(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "calendar-feed/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "ignore"))


def parse_value(raw):
    """'0.3%' → 0.3, '187K' → 187000, '3.26T' → 3.26e12, '' → None."""
    if raw is None:
        return None
    s = str(raw).strip().replace(",", "").replace("<", "").replace(">", "")
    if not s:
        return None
    mult = 1.0
    if s.endswith("%"):
        s = s[:-1]
    elif s and s[-1].upper() in "KMBT":
        mult = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}[s[-1].upper()]
        s = s[:-1]
    try:
        return float(s) * mult
    except ValueError:
        return None


# ── Fetch + cache ────────────────────────────────────────────────────────────
def _load_cache():
    try:
        with open(CACHE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cache(cache):
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f)
    except Exception:
        pass


def _normalize(raw_events):
    out = []
    for e in raw_events:
        try:
            t = dt.datetime.fromisoformat(e.get("date", ""))
            time_utc = t.astimezone(dt.timezone.utc).isoformat()
        except Exception:
            continue
        out.append({
            "event": e.get("title", ""),
            "currency": e.get("country", ""),
            "impact": e.get("impact", ""),
            "time_utc": time_utc,
            "forecast": e.get("forecast") or None,
            "previous": e.get("previous") or None,
            "actual": e.get("actual") or None,
        })
    return out


def fetch_events(force=False):
    cache = _load_cache()
    now = dt.datetime.now(dt.timezone.utc)
    fetched_at = cache.get("fetched_at")
    fresh = False
    if fetched_at and not force:
        try:
            age = (now - dt.datetime.fromisoformat(fetched_at)).total_seconds()
            fresh = age < CACHE_TTL_S
        except Exception:
            pass
    last_attempt = cache.get("last_attempt")
    in_backoff = False
    if last_attempt:
        try:
            in_backoff = (now - dt.datetime.fromisoformat(last_attempt)).total_seconds() < FETCH_BACKOFF_S
        except Exception:
            pass
    if not fresh and not in_backoff:
        try:
            raw = _get_json(FF_URL)
            cache = {"fetched_at": now.isoformat(), "events": _normalize(raw),
                     "source": "forexfactory"}
            _save_cache(cache)
        except Exception:
            # Panne réseau/rate-limit : on sert le cache stale et on note
            # l'échec pour ne pas marteler le feed (il bannit par IP)
            cache["last_attempt"] = now.isoformat()
            _save_cache(cache)
            cache = dict(cache, stale=True)
    events = cache.get("events", [])
    # Ré-applique les actuals déjà en cache (AUCUN réseau ici, le fetch
    # JBlanked est réservé au job quotidien, quota free = 1 req/jour)
    _apply_jb_cache(events, cache)
    return events


def _apply_jb_cache(events, cache):
    """Reporte les actuals du cache JBlanked sur les événements. Sans réseau.

    Un actual à 0 est ambigu (vrai 0.0% vs placeholder pré-release) : on ne
    l'accepte que si l'heure de l'événement est passée.
    """
    by_key = {}
    for it in (cache.get("jblanked") or {}).get("data") or []:
        name = (it.get("Name") or it.get("name") or "").strip().lower()
        cur = (it.get("Currency") or it.get("currency") or "").strip()
        actual = it.get("Actual") if "Actual" in it else it.get("actual")
        if name and actual not in (None, ""):
            by_key[(name, cur)] = str(actual)
    n = 0
    now = dt.datetime.now(dt.timezone.utc)
    for e in events:
        if e["actual"] is not None:
            continue
        hit = by_key.get((e["event"].strip().lower(), e["currency"]))
        if hit is None:
            continue
        if hit in ("0", "0.0"):
            # Un actual à 0 est presque toujours un placeholder JBlanked
            # (vérifié le 10/06 : CPI y/y "0.0" contre 4.2 attendu, 1h après
            # le print). On ne l'accepte que si le forecast lui-même est ~0
            # (seul cas où un vrai print 0.0 est plausible). On perd de
            # rares vrais zéros ; on ne pollue jamais l'historique.
            f = parse_value(e.get("forecast"))
            if f is None or abs(f) > 0.05:
                continue
        e["actual"] = hit
        n += 1
    return n


def daily_actuals_job(now=None):
    """Job quotidien UNIQUE d'enrichissement des actuals (quota JBlanked 1/jour).

    Déclenchement : 45 min après le dernier événement high-impact USD du jour
    (pour que le mode EVENT_DAY voie le print le jour même), sinon 21h UTC.
    À appeler à chaque cycle du watcher : no-op tant que l'heure n'est pas
    venue ou si déjà fait aujourd'hui. Alimente aussi l'historique des
    surprises (update_history)."""
    key = _env_key("JBLANKED_API_KEY")
    if not key:
        return {"status": "no_key"}
    now = now or dt.datetime.now(dt.timezone.utc)
    today = now.date().isoformat()
    cache = _load_cache()
    if cache.get("actuals_job_done") == today:
        return {"status": "already_done"}

    trigger = now.replace(hour=21, minute=0, second=0, microsecond=0)
    todays_high = []
    for e in cache.get("events", []):
        try:
            t = dt.datetime.fromisoformat(e["time_utc"])
        except Exception:
            continue
        if t.date().isoformat() == today and e["impact"] == "High" and e["currency"] == "USD":
            todays_high.append(t)
    if todays_high:
        trigger = min(trigger, max(todays_high) + dt.timedelta(minutes=45))
    if now < trigger:
        return {"status": "waiting", "trigger_utc": trigger.isoformat()}

    try:
        cache["jblanked"] = {"date": today, "data": _get_json_jb(key)}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}
    events = cache.get("events", [])
    enriched = _apply_jb_cache(events, cache)
    cache["events"] = events
    cache["actuals_job_done"] = today
    _save_cache(cache)
    added = update_history(events)
    return {"status": "ok", "enriched": enriched, "history_added": added}


def _get_json_jb(key, timeout=20):
    req = urllib.request.Request(
        "https://www.jblanked.com/news/api/forex-factory/calendar/week/",
        headers={"User-Agent": "calendar-feed/1.0",
                 "Authorization": f"Api-Key {key}"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "ignore"))


# ── Historique des surprises → z-score ───────────────────────────────────────
def _load_history():
    try:
        with open(HISTORY_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def _hist_key(e):
    return f"{e['currency']}|{e['event']}"


def update_history(events=None):
    """Enregistre (une fois) chaque release dont actual ET forecast sont connus."""
    if events is None:
        events = fetch_events()
    hist = _load_history()
    added = 0
    for e in events:
        a, f = parse_value(e.get("actual")), parse_value(e.get("forecast"))
        if a is None or f is None:
            continue
        if a == 0 and abs(f) > 0.05:
            continue  # même garde anti-placeholder que _apply_jb_cache
        # Alignement d'unités : ForexFactory écrit "-56.2B" (parsé -5.62e10),
        # JBlanked renvoie le nombre affiché brut (-55.9). Si les ordres de
        # grandeur divergent, on remet l'actual à l'échelle du forecast par
        # puissances de 10^3 ; si aucun alignement raisonnable, on jette.
        if a != 0 and f != 0 and not (1 / 1000 < abs(f / a) < 1000):
            import math
            k = round(math.log10(abs(f / a)) / 3) * 3
            a_scaled = a * (10 ** k)
            if 1 / 50 < abs(f / a_scaled) < 50:
                a = a_scaled
            else:
                continue
        key = _hist_key(e)
        rows = hist.setdefault(key, [])
        if any(r["time_utc"] == e["time_utc"] for r in rows):
            continue
        rows.append({"time_utc": e["time_utc"], "forecast": f, "actual": a,
                     "surprise": a - f})
        added += 1
    if added:
        try:
            with open(HISTORY_FILE, "w") as fh:
                json.dump(hist, fh, indent=1)
        except Exception:
            pass
    return added


def surprise_z(e):
    """z = (actual - forecast) / std des surprises historiques de cet événement.

    None tant que actual/forecast manquent ou que l'historique < 4 observations
    (il se constitue au fil de l'eau via update_history)."""
    a, f = parse_value(e.get("actual")), parse_value(e.get("forecast"))
    if a is None or f is None:
        return None
    rows = _load_history().get(_hist_key(e), [])
    surprises = [r["surprise"] for r in rows]
    if len(surprises) < MIN_HISTORY_FOR_Z:
        return None
    sd = statistics.pstdev(surprises)
    if sd <= 0:
        return None
    return round((a - f) / sd, 2)


# ── Fenêtres pré/post event ──────────────────────────────────────────────────
def pre_event_window(now=None, currencies=("USD",), within_min=PRE_EVENT_MIN):
    """Événements high-impact des devises données dans les `within_min` minutes."""
    now = now or dt.datetime.now(dt.timezone.utc)
    out = []
    for e in fetch_events():
        if e["impact"] != "High" or e["currency"] not in currencies:
            continue
        try:
            t = dt.datetime.fromisoformat(e["time_utc"])
        except Exception:
            continue
        delta_min = (t - now).total_seconds() / 60
        if 0 <= delta_min <= within_min:
            out.append(dict(e, minutes_until=round(delta_min)))
    return out


def event_mode(now=None):
    """Mode courant pour news_radar / trend_day_trigger.

    PRE_EVENT : chiffre high-impact USD dans <30 min → veto nouveaux trades.
    EVENT_DAY : release high-impact USD < 8h avec |surprise_z| > 1.
    """
    now = now or dt.datetime.now(dt.timezone.utc)
    pre = pre_event_window(now=now)
    if pre:
        names = ", ".join(f"{e['event']} (T-{e['minutes_until']}m)" for e in pre[:3])
        return {"mode": "PRE_EVENT", "events": pre, "detail": names}

    for e in fetch_events():
        if e["impact"] != "High" or e["currency"] != "USD":
            continue
        try:
            t = dt.datetime.fromisoformat(e["time_utc"])
        except Exception:
            continue
        age_h = (now - t).total_seconds() / 3600
        if 0 <= age_h <= EVENT_DAY_LOOKBACK_H:
            z = surprise_z(e)
            if z is not None and abs(z) >= EVENT_DAY_Z:
                return {"mode": "EVENT_DAY", "event": e["event"], "surprise_z": z,
                        "detail": f"{e['event']} surprise_z={z:+.1f} il y a {age_h:.1f}h"}
    return {"mode": None, "detail": ""}


if __name__ == "__main__":
    evts = fetch_events()
    print(f"événements: {len(evts)} (cache {CACHE_FILE})")
    usd_high = [e for e in evts if e["impact"] == "High" and e["currency"] == "USD"]
    for e in usd_high:
        z = surprise_z(e)
        print(f"  {e['time_utc'][:16]} {e['event']:<28} forecast={e['forecast']} "
              f"previous={e['previous']} actual={e['actual']} z={z}")
    print("pré-event:", pre_event_window() or "aucun")
    print("mode:", event_mode())
