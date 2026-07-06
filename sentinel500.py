#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║   SENTINEL-500  —  IA de trading intraday S&P 500 (US500)         ║
║   Discipline · vigilance macro · gestion du risque                ║
╚══════════════════════════════════════════════════════════════════╝
Assemble : prix T0 + TA multi-TF (15m/1H/4H/1D) + macro actions + news live
+ niveaux + psychologie/SMC → score de confluence → trade ou NON.

Leçons intégrées (héritées du gold, conservées) :
  • ANTI-FADE : pas de contre-tendance si ADX>35
  • NE PAS CHASSER l'OB (RSI>70 / StochK>90) — attendre le pullback
  • ALIGNEMENT HTF : long intraday contre 1D baissier = conviction réduite
  • Stops calibrés à la volatilité réelle (ATR)
"""

import datetime, threading
import tz
from tv_live import TVLiveClient
from tv_candles import TVCandleClient, SYMBOL_MAP
import spx_macro, spx_news, spx_levels, spx_history, spx_edge, spx_intraday, spx_fred, strategies, smc, orderflow, options, regime

ASSET = "US500"
TV_ASSET = SYMBOL_MAP["US500"]

LAYER_WEIGHTS = {"tech_1h": 2.5, "tech_4h": 2.0, "macro": 2.0, "news": 1.5,
                 "internals": 1.5, "systemic": 1.2, "smc": 1.5, "orderflow": 1.3,
                 "intraday": 1.0, "psych": 0.5}
THRESHOLDS = {"strong": 7.5, "valid": 6.5, "watch": 5.0}


# ── Sessions (heure Paris, marché cash US 15:30-22:00) ──────────────────────
def get_session():
    p = tz.paris_now()
    h, wd = p.hour, p.weekday()
    if wd >= 5:
        return {"session": "WEEKEND", "tradeable": False, "note": "Marché fermé"}
    if 15 <= h < 16:
        return {"session": "US_OPEN", "tradeable": True, "note": "Ouverture cash US — volatilité, setups principaux"}
    if 16 <= h < 18:
        return {"session": "US_AM", "tradeable": True, "note": "Matinée US — tendance s'établit"}
    if 18 <= h < 20:
        return {"session": "US_PM", "tradeable": True, "note": "Après-midi US"}
    if 20 <= h < 22:
        return {"session": "US_CLOSE", "tradeable": True, "note": "Dernière heure — squaring, volatilité"}
    if 9 <= h < 15:
        return {"session": "EU_PREMARKET", "tradeable": True, "note": "Pré-market US (futures) — direction se dessine"}
    return {"session": "OVERNIGHT", "tradeable": False, "note": "Hors séance cash — futures fins"}


# ── Scoring technique d'un timeframe ────────────────────────────────────────
def score_tf(ta):
    if not ta or "error" in ta:
        return None
    buy = sell = 0.0
    rsi = ta.get("rsi", 50); adx = ta.get("adx", 0)
    dip = ta.get("di_plus", 0); dim = ta.get("di_minus", 0)
    macd = ta.get("macd", 0); macds = ta.get("macd_sig", 0)
    close = ta.get("close", 0); ema20 = ta.get("ema20", close); ema50 = ta.get("ema50", close)
    stochk = ta.get("stoch_k", 50)
    if rsi > 70: sell += 1
    elif rsi < 30: buy += 1
    buy += 2 if macd > macds else 0; sell += 2 if macd <= macds else 0
    if adx > 20:
        if dip > dim: buy += 2
        else: sell += 2
    buy += 1 if close > ema20 else 0; sell += 1 if close <= ema20 else 0
    buy += 1 if close > ema50 else 0; sell += 1 if close <= ema50 else 0
    if stochk > 80: sell += 1
    elif stochk < 20: buy += 1
    tot = buy + sell
    if tot == 0:
        return {"score": 0, "dir": "NEUTRAL"}
    bull = buy / tot * 7
    adx_bonus = 3 if adx > 35 else (2 if adx > 25 else (1 if adx > 15 else 0))
    if buy > sell:
        return {"score": round(min(bull + adx_bonus, 10), 1), "dir": "LONG"}
    elif sell > buy:
        return {"score": round(min(sell / tot * 7 + adx_bonus, 10), 1), "dir": "SHORT"}
    return {"score": round(bull, 1), "dir": "NEUTRAL"}


# ── Psychologie / SMC ───────────────────────────────────────────────────────
def analyze_psychology(ta_1h, ta_4h, macro):
    signals, score = [], 0.0
    rsi1 = (ta_1h or {}).get("rsi", 50); rsi4 = (ta_4h or {}).get("rsi", 50)
    adx1 = (ta_1h or {}).get("adx", 0); stk = (ta_1h or {}).get("stoch_k", 50)
    vix = (macro.get("VIX", {}) or {}).get("price", 0) or 0
    if rsi1 > 72:
        score -= 1.0; signals.append(f"😬 EUPHORIE (RSI {rsi1:.0f}) — risque de pullback")
    elif rsi1 < 28:
        score += 1.0; signals.append(f"😰 CAPITULATION (RSI {rsi1:.0f}) — rebond possible")
    if stk > 92:
        score -= 0.6; signals.append(f"📍 StochK {stk:.0f} surchauffe — ne pas chasser")
    elif stk < 8:
        score += 0.6; signals.append(f"📍 StochK {stk:.0f} survente extrême")
    if abs(rsi1 - rsi4) > 15:
        signals.append(f"⚠️ Divergence RSI 1H/4H ({rsi1:.0f} vs {rsi4:.0f})")
    if adx1 > 35:
        signals.append(f"⚠️ ADX {adx1:.0f} très fort — NE PAS counter-trader (anti-fade)")
    if vix and vix < 14:
        signals.append(f"🟢 VIX bas {vix:.1f} — complaisance, marché porteur mais fragile")
    elif vix and vix > 22:
        signals.append(f"🔴 VIX élevé {vix:.1f} — peur, prudence longs")
    return {"signals": signals, "score": round(score, 2)}


# ── Analyse complète ────────────────────────────────────────────────────────
_RUN_CACHE = {}            # mémoïsation courte (audit P2) : run_analysis appelé
_RUN_TTL_S = 30            # 2x/cycle (scanner + forecast) ; le 2e appel réutilise
#                            le même résultat → réseau ÷2 et prix setup == décision.


def run_analysis(verbose=True):
    import time
    if (_RUN_CACHE.get("R") is not None
            and time.time() - _RUN_CACHE.get("ts", 0) < _RUN_TTL_S):
        return _RUN_CACHE["R"]
    results = {}
    paris = tz.paris_now()

    # Prix T0
    raw = TVLiveClient(symbols=[TV_ASSET], timeout=14).fetch()
    short = TV_ASSET.split(":")[-1]
    d = raw.get(short, {})
    price = d.get("lp"); chg = d.get("chp"); hi = d.get("high_price"); lo = d.get("low_price")
    # TradingView muet → fallback datafeed (TV→yfinance→cache) au lieu d'un prix
    # None qui ferait décider le moteur sur des données absentes (audit P1).
    price_source = "tradingview"
    if price is None:
        try:
            import datafeed
            fb = datafeed.get_price("US500")
            if fb and fb.get("lp"):
                price = fb["lp"]
                price_source = fb.get("source", "yfinance")
        except Exception:
            pass
    results.update({"price": price, "chg": chg, "high": hi, "low": lo,
                    "raw_live": d, "price_source": price_source})

    # TA multi-TF (threads)
    ta = {}
    def fetch_tf(tf):
        ta[tf] = TVCandleClient(symbols=["US500"], timeframe=tf, timeout=24).fetch_ta().get("US500", {})
    threads = [threading.Thread(target=fetch_tf, args=(tf,)) for tf in ("15m", "1h", "4h", "1d")]
    for t in threads: t.start()
    for t in threads: t.join()
    # TradingView peut rater des séries quand plusieurs WebSockets partent ensemble.
    # Fallback séquentiel pour éviter un score basé sur des timeframes absents.
    for tf in ("15m", "1h", "4h", "1d"):
        if not ta.get(tf) or "error" in ta.get(tf, {}):
            ta[tf] = TVCandleClient(symbols=["US500"], timeframe=tf, timeout=28).fetch_ta().get("US500", {})
    results["ta"] = ta

    # Macro + news + niveaux
    macro = spx_macro.fetch_macro_data()
    macro_score = spx_macro.score_macro_confluence(macro)
    results["macro"] = {"data": macro, "score": macro_score}
    news = spx_news.news_score_for_spx()
    results["news"] = news
    if price:
        results["levels"] = spx_levels.get_key_levels(price)
        results["fibs"] = spx_levels.get_fibonacci_levels(hi or price, lo or price)
        results["zone"] = spx_levels.classify_zone(price)
    psych = analyze_psychology(ta.get("1h"), ta.get("4h"), macro)
    results["psychology"] = psych
    session = get_session()
    results["session"] = session

    # Intel : étude d'événements (surprises publiées + à venir avec what-if)
    try:
        released, upcoming = spx_history.analyze_calendar_surprises()
    except Exception:
        released, upcoming = [], []
    results["intel"] = {"released": released, "upcoming": upcoming}

    # Internals (term structure VIX + breadth) + intraday (VWAP/OR)
    try:
        edge = spx_edge.full_edge()
    except Exception:
        edge = {"score": 0, "direction": "NEUTRAL", "vix_structure": {}, "breadth": {}}
    results["edge"] = edge
    try:
        intra = spx_intraday.analyze_vwap_or()
    except Exception:
        intra = {"error": "indispo", "score": 0}
    results["intraday"] = intra
    try:
        fred = spx_fred.score_fred()
    except Exception:
        fred = {"score": 0, "direction": "NEUTRAL", "signals": []}
    results["fred"] = fred
    try:
        clc = TVCandleClient(symbols=["US500"], timeframe="15m", n_bars=100, timeout=22)
        clc.fetch_ta()
        smc_res = smc.smc_analysis(clc._candles.get("US500", []))
        of_res = orderflow.analyze(clc._candles.get("US500", []))
    except Exception:
        smc_res = {"bias": "NEUTRAL", "score": 0, "signals": [], "concepts": []}
        of_res = {"score": 0, "bias": "NEUTRAL", "signals": [], "poc": None}
    results["smc"] = smc_res
    results["orderflow"] = of_res
    try:
        results["options"] = options.spx_options()
    except Exception:
        results["options"] = None
    try:
        results["regime_scalp"] = regime.detect(clc._candles.get("US500", []),
                                                 adx=(ta.get("15m", {}) or {}).get("adx"))
    except Exception:
        results["regime_scalp"] = None

    # ── Confluence ──
    s1 = score_tf(ta.get("1h")) or {"score": 0, "dir": "NEUTRAL"}
    s4 = score_tf(ta.get("4h")) or {"score": 0, "dir": "NEUTRAL"}
    def dirval(x): return 1 if x == "LONG" else (-1 if x == "SHORT" else 0)
    edge_score = edge.get("score", 0) or 0
    intra_score = intra.get("score", 0) or 0
    fred_score = fred.get("score", 0) or 0
    smc_score = smc_res.get("score", 0) or 0
    of_score = of_res.get("score", 0) or 0
    comp = (dirval(s1["dir"]) * s1["score"] * LAYER_WEIGHTS["tech_1h"]
            + dirval(s4["dir"]) * s4["score"] * LAYER_WEIGHTS["tech_4h"]
            + (1 if macro_score["direction"] == "LONG" else -1 if macro_score["direction"] == "SHORT" else 0) * abs(macro_score["score"]) * LAYER_WEIGHTS["macro"]
            + (1 if news["direction"] == "LONG" else -1 if news["direction"] == "SHORT" else 0) * abs(news["score"]) * LAYER_WEIGHTS["news"]
            + edge_score * LAYER_WEIGHTS["internals"]
            + fred_score * LAYER_WEIGHTS["systemic"]
            + smc_score * LAYER_WEIGHTS["smc"]
            + of_score * LAYER_WEIGHTS["orderflow"]
            + intra_score * LAYER_WEIGHTS["intraday"]
            + psych["score"] * LAYER_WEIGHTS["psych"])
    direction = "LONG" if comp > 0 else ("SHORT" if comp < 0 else "NEUTRAL")
    # Normalisation sur 10 (calibrée, sans gonflage)
    max_comp = (10 * LAYER_WEIGHTS["tech_1h"] + 10 * LAYER_WEIGHTS["tech_4h"]
                + 3 * LAYER_WEIGHTS["macro"] + 2.5 * LAYER_WEIGHTS["news"]
                + 2 * LAYER_WEIGHTS["internals"] + 1.5 * LAYER_WEIGHTS["systemic"]
                + 2.5 * LAYER_WEIGHTS["smc"] + 1.8 * LAYER_WEIGHTS["orderflow"]
                + 1.6 * LAYER_WEIGHTS["intraday"] + 2 * LAYER_WEIGHTS["psych"])
    score10 = round(min(abs(comp) / max_comp * 10 * 1.15, 10), 1)

    # Pénalité de DIVERGENCE : couches majeures alignées avec la direction nette
    net = dirval(direction)
    layers_dir = [dirval(s1["dir"]), dirval(s4["dir"]),
                  (1 if macro_score["direction"] == "LONG" else -1 if macro_score["direction"] == "SHORT" else 0),
                  (1 if news["direction"] == "LONG" else -1 if news["direction"] == "SHORT" else 0),
                  (1 if edge_score > 0.3 else -1 if edge_score < -0.3 else 0),
                  (1 if smc_score > 0.3 else -1 if smc_score < -0.3 else 0),
                  (1 if of_score > 0.3 else -1 if of_score < -0.3 else 0),
                  (1 if intra_score > 0.3 else -1 if intra_score < -0.3 else 0)]
    aligned = sum(1 for d in layers_dir if d == net and d != 0)
    nonzero = sum(1 for d in layers_dir if d != 0)
    if nonzero >= 2 and aligned <= nonzero / 2:   # majorité non alignée = conflit fort
        score10 = round(score10 * 0.6, 1)
    elif aligned == nonzero and nonzero >= 3:      # tout aligné = bonus convergence
        score10 = round(min(score10 * 1.15, 10), 1)

    # Alignement TF (1D)
    s1d = score_tf(ta.get("1d")) or {"score": 0, "dir": "NEUTRAL"}
    htf_conflict = (direction == "LONG" and s1d["dir"] == "SHORT") or (direction == "SHORT" and s1d["dir"] == "LONG")
    if htf_conflict:
        score10 = round(score10 * 0.8, 1)

    # ATR stops
    atr = (ta.get("1h", {}).get("close", price or 0) or (price or 0)) * 0.0035
    if (ta.get("1h", {}) or {}).get("adx", 0) > 30:
        atr *= 1.4
    stops = spx_levels.get_atr_stops(price or 0, atr) if price else {}
    results["stops"] = stops

    results["confluence"] = {
        "score": score10, "direction": direction,
        "aligned": f"{aligned}/{nonzero}", "htf_conflict": htf_conflict,
        "tech_1h": s1, "tech_4h": s4, "tech_1d": s1d,
        "tradeable": score10 >= THRESHOLDS["valid"],
    }
    results["regime"] = spx_macro.macro_regime(macro)

    # STRATÉGIE : retracement OTE (double flux) + RR ≥ 1:2 forcé
    if price and hi and lo and direction in ("LONG", "SHORT"):
        ote = strategies.ote_zone(hi, lo, direction)
        entry_zone = ote.get("sweet_spot", price)
        stop = round(lo - 0.3 * atr, 2) if direction == "LONG" else round(hi + 0.3 * atr, 2)
        results["strategy"] = {"name": "OTE_RETRACEMENT", "ote": ote,
                               "levels": strategies.build_levels(direction, entry_zone, stop)}
    else:
        results["strategy"] = None

    if verbose:
        _print_report(results)
    import time
    _RUN_CACHE["ts"] = time.time()
    _RUN_CACHE["R"] = results
    return results


def _print_report(R):
    paris = tz.paris_now()
    c = R.get("confluence", {}); ta = R.get("ta", {})
    macro = R.get("macro", {}).get("data", {}); ms = R.get("macro", {}).get("score", {})
    news = R.get("news", {}); price = R.get("price")
    print("═" * 66)
    print(f"  🛡️  SENTINEL-500 — {paris.strftime('%H:%M')} Paris  |  {R['session']['session']}")
    print("═" * 66)
    emoji = "🟢" if (R.get("chg") or 0) > 0 else "🔴"
    print(f"  {emoji} S&P 500  {price}  ({R.get('chg'):+.2f}%)  |  H={R.get('high')} L={R.get('low')}")
    vix = (macro.get('VIX', {}) or {}).get('price'); nq = (macro.get('NAS100', {}) or {}).get('chg')
    print(f"  VIX {vix}  |  NASDAQ {nq:+.2f}%  |  US10Y {(macro.get('US10Y',{}) or {}).get('chg',0):+.2f}%  |  DXY {(macro.get('DXY',{}) or {}).get('chg',0):+.2f}%")
    print(f"  🌍 Régime : {R.get('regime')}  |  📅 {R['session']['note']}")
    print("\n  📊 MULTI-TIMEFRAME")
    for tf in ("15m", "1h", "4h", "1d"):
        t = ta.get(tf, {})
        if t and "error" not in t:
            ob = " ⚠️OB" if t.get("stoch_k", 50) > 90 else (" ⚠️OS" if t.get("stoch_k", 50) < 10 else "")
            print(f"   {tf:4} RSI={t.get('rsi'):5} ADX={t.get('adx'):5} StochK={t.get('stoch_k'):5}{ob}  {t.get('rec')}")
    print(f"\n  🌐 MACRO ({ms.get('score'):+.2f} {ms.get('direction')})")
    for name, txt, sc in ms.get("signals", [])[:6]:
        mk = "🟢" if sc > 0 else ("🔴" if sc < 0 else "⚪")
        print(f"   {mk} {txt}")
    print(f"\n  📰 NEWS ({news.get('score'):+.2f} {news.get('direction')})  Posture: {news.get('context',{}).get('fundamental_bias',{}).get('fed_posture')}")
    for ev in news.get("sentiment", {}).get("breakdown", [])[:4]:
        mk = "🟢" if ev["score"] > 0 else ("🔴" if ev["score"] < 0 else "⚪")
        print(f"   {mk} {ev['event']:16} {ev['tone']:12} {ev['score']:+.2f}")
    print("\n  🧠 PSYCHO / SMC")
    for s in R.get("psychology", {}).get("signals", []):
        print(f"   → {s}")
    # Intel : étude d'événements
    intel = R.get("intel", {})
    rel = intel.get("released", []); up = intel.get("upcoming", [])
    if rel:
        print("\n  🔬 SURPRISES RÉCENTES (réaction S&P projetée vs historique)")
        for r in rel[:3]:
            mk = "🟢" if r["direction"] == "LONG" else ("🔴" if r["direction"] == "SHORT" else "⚪")
            print(f"   {mk} {r['name'][:34]:34} surprise {r['surprise']:+} → {r['direction']} ~{r['magnitude_pct']}% "
                  f"(hist {r['range']}, fiab {int(r['hit_rate']*100)}%)")
    if up:
        print("\n  🎯 PROCHAINS CATALYSEURS (what-if vs historique)")
        for u in up[:3]:
            wi = ""
            est = u.get("estimate")
            try:
                bumped = float(est) * 1.10 if abs(float(est)) > 0.01 else float(est) + 0.2
                hot = spx_history.score_surprise(u["type"], bumped, float(est))
            except Exception:
                hot = None
            if hot:
                inv = "LONG" if hot["direction"] == "SHORT" else "SHORT"
                wi = f" → actual>est: S&P {hot['direction']} ~{hot['magnitude_pct']}% | actual<est: {inv}"
            print(f"   ⏰ {spx_history.to_paris(u['time'])} Paris {u['name'][:26]:26} [poids {u['weight']}] est={est}{wi}")

    # Internals : term structure VIX + breadth
    edge = R.get("edge", {})
    if edge.get("vix_structure", {}).get("signals") or edge.get("breadth", {}).get("signals"):
        print(f"\n  🛡️ INTERNALS ({edge.get('score', 0):+.2f} {edge.get('direction')})")
        for s in edge.get("vix_structure", {}).get("signals", []):
            print(f"   {s}")
        for s in edge.get("breadth", {}).get("signals", []):
            print(f"   {s}")

    # Macro-systémique (FRED)
    fred = R.get("fred", {})
    if fred.get("signals"):
        print(f"\n  🏛️ MACRO-SYSTÉMIQUE / CRÉDIT ({fred.get('score', 0):+.2f} {fred.get('direction')})")
        for s in fred.get("signals", [])[:4]:
            print(f"   {s}")

    sm = R.get("smc", {})
    if sm.get("signals"):
        print(f"\n  🧠 SMC ({sm.get('score'):+.2f} {sm.get('bias')}) — structure {sm.get('structure')}")
        for s in sm.get("signals", [])[:5]:
            print(f"   {s}")
    of = R.get("orderflow", {})
    if of.get("signals"):
        print(f"\n  📊 ORDER FLOW ({of.get('score'):+.2f} {of.get('bias')}) [POC {of.get('poc')} · VAH {of.get('vah')} · VAL {of.get('val')}]")
        for s in of.get("signals", [])[:5]:
            print(f"   {s}")
    op = R.get("options")
    if op:
        print(f"\n  🎰 OPTIONS (SPX/CBOE) — régime {op['gex_regime']}")
        print(f"   🎯 Max Pain {op['max_pain']} · 🟥 Call wall {op['call_wall']} · 🟩 Put wall {op['put_wall']} · P/C {op['pcr']} · IV {op['iv']}%")

    # Intraday : VWAP + Opening Range
    intra = R.get("intraday", {})
    if intra and "error" not in intra:
        print(f"\n  📊 VWAP / OPENING RANGE ({intra.get('score', 0):+.2f})")
        print(f"   VWAP {intra.get('vwap')} | OR {intra.get('or_low')}–{intra.get('or_high')} ({intra.get('or_state')})")
        for s in intra.get("signals", [])[:3]:
            print(f"   {s}")
    strat = R.get("strategy")
    if strat and strat.get("levels"):
        lv = strat["levels"]; ote = strat["ote"]
        print(f"\n  🎯 STRATÉGIE : {strat['name']} (retracement double-flux, RR forcé)")
        print(f"   Zone OTE (entrée sur repli) : {ote.get('ote_low')}–{ote.get('ote_high')} (sweet spot {ote.get('sweet_spot')})")
        print(f"   Stop {lv['stop']} | TP1 {lv['tp1']} (RR 2:1) | TP2 {lv['tp2']} (3:1) | TP3 {lv['tp3']} (4:1)")
    print("─" * 66)
    bar = "█" * int(c.get("score", 0)) + "░" * (10 - int(c.get("score", 0)))
    print(f"  🎯 CONFLUENCE  [{bar}]  {c.get('score')}/10  {c.get('direction')}")
    if c.get("htf_conflict"):
        print("  ⚠️ Conflit avec 1D (HTF) → conviction réduite")
    if c.get("score", 0) >= THRESHOLDS["valid"]:
        print(f"  ✅ SIGNAL VALIDE")
    else:
        print(f"  ❌ NON — confluence insuffisante ({c.get('score')}/10 < {THRESHOLDS['valid']})")
    print("═" * 66)


if __name__ == "__main__":
    run_analysis(verbose=True)
