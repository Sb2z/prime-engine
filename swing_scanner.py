#!/usr/bin/env python3
"""
SWING EQUITY SCANNER — portefeuille actions moyen terme (2-8 sem), HORS CFD.
═══════════════════════════════════════════════════════════════════════════════
But (Sam 2026-06-30) : book LONG-ONLY d'actions Revolut (10 achats gratuits/sem),
rotation momentum, benchmarké QQQ, objectif battre l'ETF net.

PHILOSOPHIE (leçons edge_lab / audit 30-06) : on ne TIME PAS le pic, on suit des
RÈGLES. Score = composite de facteurs STANDARDS et transparents, pas du sur-ajusté.

ÉTAGE 1 — momentum cross-sectionnel + force relative vs QQQ.
ÉTAGE 2 — TIMING D'ENTRÉE SUR REPLI (on n'achète pas le blow-off top mais le repli
  dans une tendance) + OVERRIDE CATALYSEUR (un titre haut MAIS adossé à un vrai
  catalyseur structuré — upside analystes, beat de résultats, croissance — voit sa
  pénalité parabolique atténuée, jamais annulée) + CAPS SECTORIELS (diversification).

Catalyseur = données STRUCTURÉES yfinance (objectifs/reco analystes, surprise BPA,
croissance) — PAS du sentiment de gros titres (bruité + surface d'injection).

Données : yfinance (daily + fondamentaux, gratuit). Lecture seule.
CLI :  python swing_scanner.py          -> liste d'achat encadrée (7 lignes, caps secteur)
       python swing_scanner.py scan     -> scan technique brut (sans catalyseur)
"""
import warnings

warnings.filterwarnings("ignore")

BENCHMARK = "QQQ"
N_LINES = 7              # lignes du portefeuille (équipondéré)
MAX_PER_SECTOR = 2       # diversification : max de lignes par secteur
ENRICH_TOP = 22          # on ne tire les fondamentaux (lent) que pour le haut du panier
MIN_BARS = 120
MIN_DOLLAR_VOL = 5e6
CATALYST_MAX = 0.7       # un catalyseur fort annule au plus 70% de la pénalité parabolique

UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AVGO", "NFLX",
    "AMD", "SMCI", "MU", "LRCX", "KLAC", "AMAT", "ASML", "TSM", "QCOM", "ARM", "MRVL", "ANET",
    "PLTR", "SNOW", "NOW", "CRM", "PANW", "CRWD", "DDOG", "NET", "MDB", "ORCL", "ADBE", "INTU",
    "RKLB", "LUNR", "ASTS", "RTX", "LMT", "GD", "BA",
    "RIVN", "LCID", "ENPH", "FSLR", "RUN",
    "COIN", "HOOD", "PYPL", "SOFI", "MSTR", "AFRM",
    "SHOP", "UBER", "ABNB", "DASH", "SPOT", "MELI", "SE", "RBLX", "CVNA",
    "LLY", "NVO", "VRTX", "MRNA", "REGN",
    "VST", "CEG", "DELL", "GE", "CAT",
    "COST", "WMT", "JPM", "V", "MA", "AXP", "DIS",
]
UNIVERSE = list(dict.fromkeys(UNIVERSE))


def _fetch(tickers, period="9mo"):
    import yfinance as yf
    try:
        data = yf.download(tickers, period=period, interval="1d", group_by="ticker",
                           auto_adjust=True, threads=True, progress=False)
    except Exception:
        return {}   # réseau/API en panne : l'appelant doit le DIRE, pas crasher
    if data is None or data.empty:
        return {}
    out = {}
    for t in tickers:
        try:
            # avec group_by='ticker' et UN seul ticker, yfinance rend parfois un
            # MultiIndex (ticker, champ) où data[t] échoue ou garde le MultiIndex :
            # un book réduit à 1 ligne ne serait plus JAMAIS évalué (sortie ratée).
            import pandas as pd
            if isinstance(data.columns, pd.MultiIndex):
                if t not in data.columns.get_level_values(0):
                    continue
                df = data[t]
            else:
                df = data
            if df is None or df.empty or df["Close"].dropna().shape[0] < MIN_BARS:
                continue
            out[t] = df.dropna()
        except Exception:
            continue
    return out


def _rsi(c, n=14):
    d = c.diff()
    g = d.clip(lower=0).ewm(alpha=1 / n).mean()
    l = (-d.clip(upper=0)).ewm(alpha=1 / n).mean()
    rs = g / l.replace(0, 1e-9)
    return float((100 - 100 / (1 + rs)).iloc[-1])


def _metrics(df):
    c = df["Close"]
    px = float(c.iloc[-1])
    ema20 = float(c.ewm(span=20).mean().iloc[-1])
    ema50 = float(c.ewm(span=50).mean().iloc[-1])
    ema200 = float(c.ewm(span=200).mean().iloc[-1]) if len(c) >= 200 else float(c.ewm(span=len(c)).mean().iloc[-1])
    ret21 = px / float(c.iloc[-22]) - 1
    ret63 = px / float(c.iloc[-64]) - 1
    vol20 = float(c.pct_change().iloc[-20:].std()) or 1e-9
    high20 = float(c.iloc[-20:].max())
    from_high = px / high20 - 1                    # <=0 : repli depuis le plus-haut 20j
    rsi = _rsi(c)
    # timing d'entrée : on récompense le REPLI sain (~ -6% du plus-haut), pas le top
    entry = max(-0.6, 1.0 - abs(from_high + 0.06) / 0.10)
    # pénalité parabolique : suracheté (RSI) + très au-dessus de l'EMA20
    parab = max(0.0, (rsi - 75) / 10) + max(0.0, (px / ema20 - 1.12) * 10)
    return {
        "px": px, "ret21": ret21, "ret63": ret63, "vol20": vol20,
        "risk_adj": (0.5 * ret21 + 0.5 * ret63) / vol20,
        "trend": (1 if px > ema50 else 0) + (1 if ema50 > ema200 else 0),
        "rsi": rsi, "from_high": from_high, "entry": entry, "parab": parab,
        "dvol": float((df["Close"] * df["Volume"]).iloc[-20:].mean()),
    }


def _z(vals):
    import statistics as st
    if len(vals) < 2:
        return [0.0] * len(vals)
    m = st.mean(vals); sd = st.pstdev(vals) or 1e-9
    return [(v - m) / sd for v in vals]


def scan(universe=None, period="9mo"):
    """Étage 1+2 technique (sans catalyseur) : pré-classement."""
    universe = universe or UNIVERSE
    bars = _fetch(universe + [BENCHMARK], period=period)
    if BENCHMARK not in bars:
        return {"error": f"benchmark {BENCHMARK} indisponible"}
    bench = _metrics(bars[BENCHMARK])
    rows = []
    for t in universe:
        if t not in bars:
            continue
        m = _metrics(bars[t])
        if m["dvol"] < MIN_DOLLAR_VOL:
            continue
        m["ticker"] = t
        m["rs"] = m["ret63"] - bench["ret63"]
        rows.append(m)
    if not rows:
        return {"error": "aucun titre exploitable"}
    zra = _z([r["risk_adj"] for r in rows]); zrs = _z([r["rs"] for r in rows])
    for r, a, b in zip(rows, zra, zrs):
        # tendance + force relative + TIMING D'ENTRÉE (repli) - pénalité parabolique
        r["tech"] = round(0.7 * a + 0.6 * b + 0.4 * r["trend"] + 0.8 * r["entry"] - r["parab"], 3)
    rows.sort(key=lambda r: r["tech"], reverse=True)
    return {"bench": bench, "rows": rows, "n": len(rows)}


def _catalyst(ticker):
    """Score catalyseur STRUCTURÉ [0..1] + secteur. Lent (.info) -> top du panier only."""
    import yfinance as yf
    try:
        info = yf.Ticker(ticker).info
    except Exception:
        return {"sector": "?", "cat": 0.0, "upside": None, "reco": "?", "growth": None}
    cur = info.get("currentPrice"); tgt = info.get("targetMeanPrice")
    upside = (tgt / cur - 1) if (cur and tgt) else 0.0
    reco = (info.get("recommendationKey") or "").lower()
    reco_s = {"strong_buy": 1.0, "buy": 0.6, "hold": 0.0, "underperform": -0.5, "sell": -1.0}.get(reco, 0.0)
    growth = info.get("revenueGrowth") or 0.0
    nanalysts = info.get("numberOfAnalystOpinions") or 0
    # composite borné [0..1] : upside analystes + reco + croissance, atténué si peu d'analystes
    raw = 0.45 * min(max(upside, 0) / 0.40, 1) + 0.35 * max(reco_s, 0) + 0.20 * min(max(growth, 0) / 0.40, 1)
    if nanalysts < 5:
        raw *= 0.5
    return {"sector": info.get("sector") or "?", "cat": round(min(raw, 1.0), 3),
            "upside": upside, "reco": reco or "?", "growth": growth, "nanalysts": nanalysts}


def recommend(n_lines=N_LINES, max_per_sector=MAX_PER_SECTOR, enrich_top=ENRICH_TOP,
              exclude=None, sector_start=None):
    """Pipeline complet : technique -> catalyseur sur le haut -> override -> caps secteur.
    exclude = tickers déjà détenus (exclus des achats). sector_start = secteurs déjà
    occupés par le portefeuille (les caps tiennent sur TOUT le book, pas juste les neufs)."""
    exclude = exclude or set()
    res = scan()
    if res.get("error"):
        return res
    top = [r for r in res["rows"] if r["ticker"] not in exclude][:enrich_top]
    for r in top:                       # enrichissement fondamental (lent) du haut du panier
        info = _catalyst(r["ticker"])
        r.update(info)
        # OVERRIDE : le catalyseur annule jusqu'à CATALYST_MAX de la pénalité parabolique
        r["final"] = round(r["tech"] + r["parab"] * CATALYST_MAX * r["cat"], 3)
    top.sort(key=lambda r: r["final"], reverse=True)
    # sélection avec caps sectoriels (diversification sur tout le portefeuille)
    picks, sectors = [], dict(sector_start or {})
    for r in top:
        s = r.get("sector", "?")
        if sectors.get(s, 0) >= max_per_sector:
            r["skipped"] = f"cap secteur {s}"
            continue
        picks.append(r); sectors[s] = sectors.get(s, 0) + 1
        if len(picks) >= n_lines:
            break
    return {"bench": res["bench"], "picks": picks, "considered": top, "n": res["n"]}


def _print_reco(res):
    if res.get("error"):
        print("ERREUR:", res["error"]); return
    b = res["bench"]
    print(f"Benchmark {BENCHMARK}: 1m {b['ret21']*100:+.1f}%  3m {b['ret63']*100:+.1f}%   "
          f"({res['n']} titres) — portefeuille {N_LINES} lignes équipondérées, max {MAX_PER_SECTOR}/secteur\n")
    print(f"  LISTE D'ACHAT (encadrée) :")
    print(f"  {'#':>2} {'ticker':6s} {'final':>6s} {'px':>9s} {'3m%':>7s} {'vsQQQ':>6s} "
          f"{'RSI':>4s} {'repli':>6s} {'cat':>4s} {'upside':>7s} {'secteur':16s}")
    for i, r in enumerate(res["picks"], 1):
        up = f"{r['upside']*100:+.0f}%" if r.get("upside") is not None else "?"
        flag = "⚡cata" if (r["parab"] > 0.5 and r["cat"] > 0.4) else ("⛔para" if r["parab"] > 0.5 else "")
        print(f"  {i:>2} {r['ticker']:6s} {r['final']:>6.2f} {r['px']:9.2f} {r['ret63']*100:+7.1f} "
              f"{r['rs']*100:+6.1f} {r['rsi']:>4.0f} {r['from_high']*100:>5.1f}% {r['cat']:>4.2f} "
              f"{up:>7s} {str(r.get('sector'))[:16]:16s} {flag}")
    skipped = [r for r in res["considered"] if r.get("skipped")][:5]
    if skipped:
        print("\n  écartés (diversification) :", ", ".join(f"{r['ticker']}({r['skipped']})" for r in skipped))


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "scan":
        from pprint import pprint
        r = scan()
        for x in r.get("rows", [])[:15]:
            print(f"{x['ticker']:6s} tech={x['tech']:+.2f} 3m={x['ret63']*100:+.0f}% rsi={x['rsi']:.0f} "
                  f"repli={x['from_high']*100:+.1f}% parab={x['parab']:.2f}")
    else:
        _print_reco(recommend())
