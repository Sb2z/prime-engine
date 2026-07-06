#!/usr/bin/env python3
"""COT FEED — positionnement spéculatif CFTC hebdomadaire (gratuit).

Source : API Socrata publique de la CFTC (Legacy Futures Only, dataset
6dca-aqww), rapport publié le vendredi soir sur les positions du mardi.

Features par actif :
  net_specs    : positions nettes non-commerciales (long - short)
  change_4w    : variation sur 4 semaines
  pctile_3y    : percentile du net sur 3 ans (0 = extrême short, 100 = extrême long)

Cache 24h (le rapport est hebdomadaire, inutile de marteler l'API).
Alimente la colonne cot_pctile du feature store.
"""

import datetime as dt
import json
import urllib.parse
import urllib.request

API = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"
CACHE_FILE = "/Users/sam/trading/cot_cache.json"
CACHE_TTL_S = 24 * 3600
WEEKS_3Y = 156

MARKETS = {
    "GOLD": "GOLD - COMMODITY EXCHANGE INC.",
    "US500": "E-MINI S&P 500 - CHICAGO MERCANTILE EXCHANGE",
}


def _load_cache():
    try:
        with open(CACHE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cache(c):
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(c, f)
    except Exception:
        pass


def _fetch_market(market_name):
    params = urllib.parse.urlencode({
        "$select": "report_date_as_yyyy_mm_dd,noncomm_positions_long_all,"
                   "noncomm_positions_short_all,open_interest_all",
        "$where": f"market_and_exchange_names='{market_name}'",
        "$order": "report_date_as_yyyy_mm_dd DESC",
        "$limit": WEEKS_3Y,
    })
    req = urllib.request.Request(f"{API}?{params}",
                                 headers={"User-Agent": "cot-feed/1.0"})
    with urllib.request.urlopen(req, timeout=25) as r:
        rows = json.loads(r.read().decode())
    out = []
    for row in rows:
        try:
            out.append({
                "date": row["report_date_as_yyyy_mm_dd"][:10],
                "net": int(row["noncomm_positions_long_all"])
                       - int(row["noncomm_positions_short_all"]),
                "oi": int(row.get("open_interest_all") or 0),
            })
        except Exception:
            continue
    return out  # trié du plus récent au plus ancien


def snapshot(asset, force=False):
    """Features COT pour un actif. Sert le cache (24h), stale si API down."""
    market = MARKETS.get(asset)
    if not market:
        return None
    cache = _load_cache()
    now = dt.datetime.now(dt.timezone.utc)
    entry = cache.get(asset) or {}
    fresh = False
    if entry.get("fetched_at") and not force:
        try:
            age = (now - dt.datetime.fromisoformat(entry["fetched_at"])).total_seconds()
            fresh = age < CACHE_TTL_S
        except Exception:
            pass
    if not fresh:
        try:
            rows = _fetch_market(market)
            if rows:
                entry = {"fetched_at": now.isoformat(), "rows": rows}
                cache[asset] = entry
                _save_cache(cache)
        except Exception:
            if not entry:
                return None
            entry = dict(entry, stale=True)

    rows = entry.get("rows") or []
    if not rows:
        return None
    nets = [r["net"] for r in rows]
    current = nets[0]
    below = sum(1 for n in nets if n <= current)
    return {
        "asset": asset,
        "report_date": rows[0]["date"],
        "net_specs": current,
        "change_4w": current - nets[4] if len(nets) > 4 else None,
        "pctile_3y": round(below / len(nets) * 100, 1),
        "weeks": len(nets),
        "stale": bool(entry.get("stale")),
    }


if __name__ == "__main__":
    for asset in MARKETS:
        s = snapshot(asset)
        if s:
            print(f"{asset}: net specs {s['net_specs']:+,} (rapport {s['report_date']}) "
                  f"Δ4s {s['change_4w']:+,} · percentile 3 ans {s['pctile_3y']} "
                  f"({s['weeks']} semaines){' [STALE]' if s['stale'] else ''}")
        else:
            print(f"{asset}: indisponible")
