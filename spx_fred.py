#!/usr/bin/env python3
"""
SENTINEL-500 — Couche macro-systémique (FRED)
══════════════════════════════════════════════════════════════════
Le signal de stress que le prix ne montre pas encore :
  • HY OAS (spreads crédit haut rendement) — l'écartement = stress systémique
  • 2s10s (courbe des taux) — inversion/re-steepening = signal de cycle
  • NFCI (conditions financières Chicago Fed) — resserrement = frein
Données quotidiennes/hebdo → cache 12h. Score positif = bullish S&P.
"""

import urllib.request, json, os, time, datetime

CACHE = "/Users/sam/trading/fred_cache.json"
TTL = 43200  # 12h

SERIES = {
    "HY_OAS":  "BAMLH0A0HYM2",   # High Yield credit spread (%)
    "IG_OAS":  "BAMLC0A0CM",     # Investment Grade spread (%)
    "T10Y2Y":  "T10Y2Y",         # courbe 10Y-2Y
    "NFCI":    "NFCI",           # conditions financières (hebdo)
}


def _key():
    k = os.environ.get("FRED_API_KEY")
    if k:
        return k
    try:
        for line in open("/Users/sam/trading/.env"):
            if line.startswith("FRED_API_KEY"):
                return line.split("=", 1)[1].strip()
    except Exception:
        return None


def _fetch_series(sid, key, n=25):
    url = (f"https://api.stlouisfed.org/fred/series/observations?series_id={sid}"
           f"&api_key={key}&file_type=json&sort_order=desc&limit={n}")
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "sentinel500/1.0"})
            d = json.load(urllib.request.urlopen(req, timeout=12))
            return [(o["date"], float(o["value"])) for o in d["observations"] if o["value"] not in (".", "")]
        except Exception:
            time.sleep(0.5)
    return []


def fetch_fred():
    # cache
    try:
        c = json.load(open(CACHE))
        if time.time() - c.get("ts", 0) < TTL:
            return c["data"]
    except Exception:
        pass
    key = _key()
    if not key:
        return {}
    data = {}
    for name, sid in SERIES.items():
        vals = _fetch_series(sid, key)
        time.sleep(0.35)   # évite le throttling FRED
        if vals:
            latest = vals[0][1]
            wk = vals[5][1] if len(vals) > 5 else latest      # ~5 jours
            mo = vals[20][1] if len(vals) > 20 else latest     # ~20 jours
            data[name] = {"latest": latest, "d5": round(latest - wk, 3),
                          "d20": round(latest - mo, 3), "date": vals[0][0]}
    try:
        json.dump({"ts": time.time(), "data": data}, open(CACHE, "w"))
    except Exception:
        pass
    return data


def score_fred():
    """Analyse macro-systémique → score + signaux pour S&P."""
    d = fetch_fred()
    if not d:
        return {"score": 0, "signals": ["⚪ FRED indisponible"], "data": {}}
    signals, score = [], 0.0

    hy = d.get("HY_OAS")
    if hy:
        lvl, ch5 = hy["latest"], hy["d5"]
        bps = lvl * 100
        if bps < 300:
            score += 0.6; signals.append(f"🟢 Spreads HY {bps:.0f}bps bas → crédit calme, risk-on (soutien actions)")
        elif bps < 450:
            score += 0.1; signals.append(f"⚪ Spreads HY {bps:.0f}bps normaux")
        elif bps < 600:
            score -= 0.8; signals.append(f"🟠 Spreads HY {bps:.0f}bps élevés → stress crédit, prudence")
        else:
            score -= 1.5; signals.append(f"🔴 Spreads HY {bps:.0f}bps très élevés → stress systémique, bearish")
        if ch5 * 100 >= 25:
            score -= 0.8; signals.append(f"🔴 Spreads HY s'écartent vite ({ch5*100:+.0f}bps/5j) → risk-off naissant")
        elif ch5 * 100 <= -15:
            score += 0.4; signals.append(f"🟢 Spreads HY se resserrent ({ch5*100:+.0f}bps/5j) → appétit risque")

    yc = d.get("T10Y2Y")
    if yc:
        lvl, ch20 = yc["latest"], yc["d20"]
        if lvl < 0:
            signals.append(f"🟠 Courbe 2s10s inversée ({lvl:+.2f}) → signal de cycle tardif (surveiller)")
        else:
            signals.append(f"⚪ Courbe 2s10s {lvl:+.2f}")
        if lvl > 0 and (lvl - ch20) < 0:   # re-steepening depuis inversion
            signals.append(f"⚠️ Re-steepening de la courbe → historiquement pré-récession, vigilance")

    nfci = d.get("NFCI")
    if nfci:
        lvl = nfci["latest"]
        if lvl > 0.1:
            score -= 0.5; signals.append(f"🔴 Conditions financières resserrées (NFCI {lvl:+.2f}) → frein actions")
        elif lvl < -0.2:
            score += 0.3; signals.append(f"🟢 Conditions financières accommodantes (NFCI {lvl:+.2f}) → soutien")
        else:
            signals.append(f"⚪ Conditions financières neutres (NFCI {lvl:+.2f})")

    direction = "LONG" if score >= 0.5 else ("SHORT" if score <= -0.5 else "NEUTRAL")
    return {"score": round(score, 2), "direction": direction, "signals": signals, "data": d}


if __name__ == "__main__":
    r = score_fred()
    print(f"\n🏛️ MACRO-SYSTÉMIQUE (FRED) — score {r['score']:+.2f} {r.get('direction')}\n")
    for s in r["signals"]:
        print(f"   {s}")
    print("\n  Données brutes :")
    for k, v in r["data"].items():
        print(f"   {k}: {v}")
