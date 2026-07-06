#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║   AURUM, IA de trading intraday GOLD (XAUUSD)                  ║
║   Le pendant de SENTINEL-500, adapté à l'or                       ║
║   Fondamental pour anticiper · technique pour les setups          ║
╚══════════════════════════════════════════════════════════════════╝
Couches : TA multi-TF + macro (DXY inverse, taux réels, silver) + news (refuge)
+ ÉTUDE D'ÉVÉNEMENTS + INTERNALS OR (DXY momentum, ratio or/argent) + niveaux/Fib
+ psychologie/SMC → confluence → trade ou NON.

Ce qui marche le mieux sur l'or (pondéré en conséquence) :
  • DXY inverse = driver #1 · taux réels = le vrai fondamental
  • Fibonacci & niveaux ronds ($50/$100) = l'or les respecte fortement
  • Refuge géopolitique (escalade = haussier, inverse des actions)
  • Sweeps de liquidité / ADX fort = ne jamais counter-trader (règle Kasper)
"""
import datetime, threading
import tz
from tv_live import TVLiveClient
from tv_candles import TVCandleClient, SYMBOL_MAP
import gold_macro, gold_news, gold_levels, gold_history, gold_edge, strategies, smc, micro_rebound, orderflow, options, regime

ASSET = "GOLD"
TV_ASSET = SYMBOL_MAP["GOLD"]

# Poids spécifiques OR. SMC + order flow (POC/delta) = couches d'exécution importantes.
LAYER_WEIGHTS = {"tech_1h": 2.5, "tech_4h": 2.0, "macro": 2.2, "news": 1.5,
                 "edge": 2.0, "smc": 1.5, "orderflow": 1.3, "levels": 1.2, "psych": 0.6}
THRESHOLDS = {"strong": 7.5, "valid": 6.5, "watch": 5.0}


def get_session():
    p = tz.paris_now()
    h, wd = p.hour, p.weekday()
    if wd >= 5:
        return {"session": "WEEKEND", "tradeable": False, "note": "Marché fermé"}
    if 1 <= h < 9:
        return {"session": "ASIAN", "tradeable": True, "note": "Range asiatique, accumulation, faible volatilité"}
    if 9 <= h < 13:
        return {"session": "LONDON", "tradeable": True, "note": "London, breakout du range asiatique, DXY moves"}
    if 13 <= h < 15:
        return {"session": "PRE_NY", "tradeable": True, "note": "Pré-NY, données US, volatilité monte"}
    if 15 <= h < 18:
        return {"session": "NY", "tradeable": True, "note": "NY, setups principaux, réaction macro US"}
    if 18 <= h < 22:
        return {"session": "NY_PM", "tradeable": True, "note": "NY après-midi / clôture"}
    return {"session": "OVERNIGHT", "tradeable": False, "note": "Overnight, liquidité fine, gaps"}


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
        buy += 2 if dip > dim else 0; sell += 2 if dip <= dim else 0
    buy += 1 if close > ema20 else 0; sell += 1 if close <= ema20 else 0
    buy += 1 if close > ema50 else 0; sell += 1 if close <= ema50 else 0
    if stochk > 80: sell += 1
    elif stochk < 20: buy += 1
    tot = buy + sell
    if tot == 0:
        return {"score": 0, "dir": "NEUTRAL"}
    adx_bonus = 3 if adx > 35 else (2 if adx > 25 else (1 if adx > 15 else 0))
    if buy > sell:
        return {"score": round(min(buy / tot * 7 + adx_bonus, 10), 1), "dir": "LONG"}
    elif sell > buy:
        return {"score": round(min(sell / tot * 7 + adx_bonus, 10), 1), "dir": "SHORT"}
    return {"score": round(buy / tot * 7, 1), "dir": "NEUTRAL"}


def analyze_psychology(ta_1h, ta_4h, edge):
    signals, score = [], 0.0
    rsi1 = (ta_1h or {}).get("rsi", 50); rsi4 = (ta_4h or {}).get("rsi", 50)
    adx1 = (ta_1h or {}).get("adx", 0); stk = (ta_1h or {}).get("stoch_k", 50)
    if rsi1 > 72:
        score -= 1.0; signals.append(f"😬 GREED (RSI {rsi1:.0f}), risque retournement")
    elif rsi1 < 28:
        score += 1.0; signals.append(f"😰 PEUR/capitulation (RSI {rsi1:.0f}), rebond possible")
    if stk > 92:
        score -= 0.6; signals.append(f"📍 StochK {stk:.0f} surchauffe, ne pas chasser")
    elif stk < 8:
        score += 0.6; signals.append(f"📍 StochK {stk:.0f} survente extrême, rebond imminent probable")
    if abs(rsi1 - rsi4) > 15:
        signals.append(f"⚠️ Divergence RSI 1H/4H ({rsi1:.0f} vs {rsi4:.0f})")
    if adx1 > 35:
        signals.append(f"⚠️ ADX {adx1:.0f} très fort, NE PAS counter-trader (règle Kasper)")
    return {"signals": signals, "score": round(score, 2)}


_RUN_CACHE = {}            # mémoïsation courte (audit P2) : run_analysis est
_RUN_TTL_S = 30            # appelé 2x/cycle (scanner + forecast) ; le 2e appel
#                            réutilise le même R → réseau ÷2 et prix setup ==
#                            prix décision. TTL << intervalle de cycle (~336s).


def run_analysis(verbose=True):
    import time
    if (_RUN_CACHE.get("R") is not None
            and time.time() - _RUN_CACHE.get("ts", 0) < _RUN_TTL_S):
        return _RUN_CACHE["R"]
    R = {}
    raw = TVLiveClient(symbols=[TV_ASSET], timeout=14).fetch()
    d = raw.get(TV_ASSET.split(":")[-1], {})
    price, chg, hi, lo = d.get("lp"), d.get("chp"), d.get("high_price"), d.get("low_price")
    # TradingView muet → fallback datafeed (TV→yfinance→cache) au lieu d'un prix
    # None qui ferait décider le moteur sur des données absentes (audit P1).
    price_source = "tradingview"
    if price is None:
        try:
            import datafeed
            fb = datafeed.get_price("GOLD")
            if fb and fb.get("lp"):
                price = fb["lp"]
                price_source = fb.get("source", "yfinance")
        except Exception:
            pass
    R.update({"price": price, "chg": chg, "high": hi, "low": lo,
              "raw_live": d, "price_source": price_source})

    ta = {}
    def fetch_tf(tf):
        ta[tf] = TVCandleClient(symbols=["GOLD"], timeframe=tf, timeout=24).fetch_ta().get("GOLD", {})
    threads = [threading.Thread(target=fetch_tf, args=(tf,)) for tf in ("15m", "1h", "4h", "1d")]
    for t in threads: t.start()
    for t in threads: t.join()
    # TradingView peut rater des séries quand plusieurs WebSockets partent ensemble.
    # Fallback séquentiel pour éviter un score basé sur des timeframes absents.
    for tf in ("15m", "1h", "4h", "1d"):
        if not ta.get(tf) or "error" in ta.get(tf, {}):
            ta[tf] = TVCandleClient(symbols=["GOLD"], timeframe=tf, timeout=28).fetch_ta().get("GOLD", {})
    R["ta"] = ta

    macro = gold_macro.fetch_macro_data()
    macro_score = gold_macro.score_macro_confluence(macro)
    R["macro"] = {"data": macro, "score": macro_score}
    news = gold_news.news_score_for_gold()
    R["news"] = news
    edge = gold_edge.full_edge()
    R["edge"] = edge
    # SMC : détection sur bougies 15m (structure, OB, FVG, liquidité, BOS/CHoCH)
    try:
        clc = TVCandleClient(symbols=["GOLD"], timeframe="15m", n_bars=100, timeout=22)
        clc.fetch_ta()
        smc_res = smc.smc_analysis(clc._candles.get("GOLD", []))
        of_res = orderflow.analyze(clc._candles.get("GOLD", []))
    except Exception:
        smc_res = {"bias": "NEUTRAL", "score": 0, "signals": [], "concepts": []}
        of_res = {"score": 0, "bias": "NEUTRAL", "signals": [], "poc": None}
    R["smc"] = smc_res
    R["orderflow"] = of_res
    try:
        R["options"] = options.gold_options(price)
    except Exception:
        R["options"] = None
    try:
        R["regime_scalp"] = regime.detect(clc._candles.get("GOLD", []),
                                           adx=(ta.get("15m", {}) or {}).get("adx"))
    except Exception:
        R["regime_scalp"] = None
    # SCALP : micro-rebonds entre order blocks sur 5m (stratégie gagnante de Sam)
    try:
        c5 = TVCandleClient(symbols=["GOLD"], timeframe="5m", n_bars=80, timeout=20)
        c5.fetch_ta()
        R["scalp"] = micro_rebound.detect_micro_rebound(
            c5._candles.get("GOLD", []), trend=smc_res.get("structure", "RANGE"))
    except Exception:
        R["scalp"] = None
    if price:
        R["levels"] = gold_levels.get_key_levels(price)
        R["fibs"] = gold_levels.get_fibonacci_levels(hi or price, lo or price)
        R["zone"] = gold_levels.classify_zone(price)
    psych = analyze_psychology(ta.get("1h"), ta.get("4h"), edge)
    R["psychology"] = psych
    R["session"] = get_session()
    try:
        rel, up = gold_history.analyze_calendar_surprises()
    except Exception:
        rel, up = [], []
    R["intel"] = {"released": rel, "upcoming": up}

    # Confluence
    s1 = score_tf(ta.get("1h")) or {"score": 0, "dir": "NEUTRAL"}
    s4 = score_tf(ta.get("4h")) or {"score": 0, "dir": "NEUTRAL"}
    s1d = score_tf(ta.get("1d")) or {"score": 0, "dir": "NEUTRAL"}
    def dv(x): return 1 if x == "LONG" else (-1 if x == "SHORT" else 0)
    def md(x): return 1 if x == "LONG" else (-1 if x == "SHORT" else 0)
    smc_score = smc_res.get("score", 0) or 0
    of_score = of_res.get("score", 0) or 0
    comp = (dv(s1["dir"]) * s1["score"] * LAYER_WEIGHTS["tech_1h"]
            + dv(s4["dir"]) * s4["score"] * LAYER_WEIGHTS["tech_4h"]
            + md(macro_score["direction"]) * abs(macro_score["score"]) * LAYER_WEIGHTS["macro"]
            + md(news["direction"]) * abs(news["score"]) * LAYER_WEIGHTS["news"]
            + edge["score"] * LAYER_WEIGHTS["edge"]
            + smc_score * LAYER_WEIGHTS["smc"]
            + of_score * LAYER_WEIGHTS["orderflow"]
            + psych["score"] * LAYER_WEIGHTS["psych"])
    direction = "LONG" if comp > 0 else ("SHORT" if comp < 0 else "NEUTRAL")
    max_comp = (10 * LAYER_WEIGHTS["tech_1h"] + 10 * LAYER_WEIGHTS["tech_4h"]
                + 3 * LAYER_WEIGHTS["macro"] + 2.5 * LAYER_WEIGHTS["news"]
                + 3 * LAYER_WEIGHTS["edge"] + 2.5 * LAYER_WEIGHTS["smc"]
                + 1.8 * LAYER_WEIGHTS["orderflow"] + 2 * LAYER_WEIGHTS["psych"])
    score10 = round(min(abs(comp) / max_comp * 10 * 1.15, 10), 1)

    net = dv(direction)
    layers = [dv(s1["dir"]), dv(s4["dir"]), md(macro_score["direction"]), md(news["direction"]),
              (1 if edge["score"] > 0.3 else -1 if edge["score"] < -0.3 else 0),
              (1 if smc_score > 0.3 else -1 if smc_score < -0.3 else 0),
              (1 if of_score > 0.3 else -1 if of_score < -0.3 else 0)]
    aligned = sum(1 for x in layers if x == net and x != 0)
    nonzero = sum(1 for x in layers if x != 0)
    if nonzero >= 2 and aligned <= nonzero / 2:
        score10 = round(score10 * 0.6, 1)
    elif aligned == nonzero and nonzero >= 3:
        score10 = round(min(score10 * 1.15, 10), 1)
    htf_conflict = (direction == "LONG" and s1d["dir"] == "SHORT") or (direction == "SHORT" and s1d["dir"] == "LONG")
    if htf_conflict:
        score10 = round(score10 * 0.8, 1)

    atr = (ta.get("1h", {}).get("close", price or 0) or (price or 0)) * 0.004
    if (ta.get("1h", {}) or {}).get("adx", 0) > 30:
        atr *= 1.5
    R["stops"] = gold_levels.get_atr_stops(price or 0, atr) if price else {}
    R["confluence"] = {"score": score10, "direction": direction, "aligned": f"{aligned}/{nonzero}",
                       "htf_conflict": htf_conflict, "tech_1h": s1, "tech_4h": s4, "tech_1d": s1d,
                       "tradeable": score10 >= THRESHOLDS["valid"]}
    R["regime"] = gold_macro.macro_regime(macro)

    # STRATÉGIE : retracement OTE (double flux) + RR ≥ 1:2 forcé
    if price and hi and lo and direction in ("LONG", "SHORT"):
        ote = strategies.ote_zone(hi, lo, direction)
        # entrée = sweet spot OTE ; stop au-delà de la jambe ; TP RR-compliant
        entry_zone = ote.get("sweet_spot", price)
        stop = round(lo - 0.3 * atr, 2) if direction == "LONG" else round(hi + 0.3 * atr, 2)
        lv = strategies.build_levels(direction, entry_zone, stop)
        R["strategy"] = {"name": "OTE_RETRACEMENT", "ote": ote, "levels": lv}
    else:
        R["strategy"] = None
    if verbose:
        _print(R)
    import time
    _RUN_CACHE["ts"] = time.time()
    _RUN_CACHE["R"] = R
    return R


def _print(R):
    p = tz.paris_now()
    c = R["confluence"]; ta = R["ta"]; macro = R["macro"]["data"]; ms = R["macro"]["score"]
    news = R["news"]; edge = R["edge"]
    print("═" * 66)
    print(f"  🥇 AURUM (GOLD/XAUUSD), {p.strftime('%H:%M')} Paris  |  {R['session']['session']}")
    print("═" * 66)
    em = "🟢" if (R.get("chg") or 0) > 0 else "🔴"
    print(f"  {em} GOLD  ${R.get('price')}  ({R.get('chg'):+.2f}%)  |  H=${R.get('high')} L=${R.get('low')}")
    print(f"  DXY {(macro.get('DXY',{}) or {}).get('chg',0):+.2f}%  |  Silver {(macro.get('SILVER',{}) or {}).get('chg',0):+.2f}%  |  US10Y {(macro.get('US10Y',{}) or {}).get('chg',0):+.2f}%  |  ratio or/argent {edge.get('gold_silver_ratio')}")
    print(f"  🌍 Régime {R.get('regime')}  |  📅 {R['session']['note']}")
    print("\n  📊 MULTI-TIMEFRAME")
    for tf in ("15m", "1h", "4h", "1d"):
        t = ta.get(tf, {})
        if t and "error" not in t:
            ob = " ⚠️OB" if t.get("stoch_k", 50) > 90 else (" ⚠️OS" if t.get("stoch_k", 50) < 10 else "")
            print(f"   {tf:4} RSI={t.get('rsi'):5} ADX={t.get('adx'):5} StochK={t.get('stoch_k'):5}{ob}  {t.get('rec')}")
    print(f"\n  🌐 MACRO ({ms.get('score'):+.2f} {ms.get('direction')})  [DXY inverse · taux réels · silver]")
    for n, txt, s in ms.get("signals", [])[:5]:
        if s != 0:
            print(f"   {'🟢' if s>0 else '🔴'} {txt}")
    print(f"\n  🥇 INTERNALS OR ({edge.get('score'):+.2f} {edge.get('direction')})")
    for s in edge.get("signals", [])[:5]:
        print(f"   {s}")
    sm = R.get("smc", {})
    if sm.get("signals"):
        print(f"\n  🧠 SMC ({sm.get('score'):+.2f} {sm.get('bias')}), structure {sm.get('structure')}")
        for s in sm.get("signals", [])[:5]:
            print(f"   {s}")
    of = R.get("orderflow", {})
    if of.get("signals"):
        print(f"\n  📊 ORDER FLOW ({of.get('score'):+.2f} {of.get('bias')}) [POC {of.get('poc')} · VAH {of.get('vah')} · VAL {of.get('val')}]")
        for s in of.get("signals", [])[:5]:
            print(f"   {s}")
    op = R.get("options")
    if op:
        print(f"\n  🎰 OPTIONS (CBOE/GLD), régime {op['gex_regime']}")
        print(f"   🎯 Max Pain ${op['max_pain_u']} (aimant) · 🟥 Call wall ${op['call_wall_u']} (résist.) · 🟩 Put wall ${op['put_wall_u']} (support)")
        print(f"   Put/Call {op['pcr']} · IV {op['iv']}%")
    rg = R.get("regime_scalp")
    if rg:
        v = "✅ SCALPE" if rg["scalp_ok"] else "⛔ NE PAS SCALPER"
        print(f"\n  📐 RÉGIME SCALP : {rg['regime']}, {v} (WR attendu {rg['expected_wr']})")
        print(f"   ER {rg['er']} · ADX 15m {rg['adx']} · {rg['note']}")
    print(f"\n  📰 NEWS/FONDAMENTAL ({news.get('score'):+.2f} {news.get('direction')})  Fed: {news.get('context',{}).get('fundamental_bias',{}).get('fed_posture')}")
    rel = R["intel"]["released"]; up = R["intel"]["upcoming"]
    if rel:
        print("\n  🔬 SURPRISES (réaction or projetée)")
        for r in rel[:3]:
            mk = "🟢" if r["direction"] == "LONG" else "🔴"
            print(f"   {mk} {r['name'][:30]:30} surp {r['surprise']:+} → {r['direction']} ~{r['magnitude_pct']}% (fiab {int(r['hit_rate']*100)}%)")
    if up:
        print("\n  🎯 CATALYSEURS À VENIR")
        for u in up[:3]:
            print(f"   ⏰ {gold_history.to_paris(u['time'])} Paris {u['name'][:26]:26} [poids {u['weight']}] est={u['estimate']}")
    print("\n  🧠 PSYCHO / SMC")
    for s in R["psychology"]["signals"]:
        print(f"   → {s}")
    fibs = R.get("fibs", {})
    if fibs and R.get("price"):
        print("\n  📐 FIBONACCI (l'or les respecte)")
        for k in ("0.382", "0.500", "0.618", "0.786"):
            v = fibs.get(k)
            mark = " ←← PRIX" if v and abs(v - R["price"]) < (R["price"] * 0.0015) else ""
            print(f"   Fib {k}: ${v}{mark}")
    sc = R.get("scalp")
    if sc and sc.get("setup"):
        s = sc["setup"]
        al = "✅ avec tendance" if s.get("aligned_with_trend") else "⚠️ contre-tendance (exit ultra-rapide)"
        print(f"\n  ⚡ SCALP MICRO-REBOND ({al})")
        print(f"   {s['direction']} @ {s['entry']} | Stop {s['stop']} | TP rapide {s['tp_fast']} | RR {s['rr']}")
        print(f"   {s['note']}")
    elif sc and sc.get("stalling"):
        print(f"\n  ⚡ SCALP : consolidation détectée (structure {sc.get('structure')}), micro-rebond imminent possible")

    strat = R.get("strategy")
    if strat and strat.get("levels"):
        lv = strat["levels"]; ote = strat["ote"]
        print(f"\n  🎯 STRATÉGIE : {strat['name']} (retracement double-flux, RR forcé)")
        print(f"   Zone OTE (entrée sur repli) : ${ote.get('ote_low')}-${ote.get('ote_high')} (sweet spot ${ote.get('sweet_spot')})")
        print(f"   Stop ${lv['stop']} | TP1 ${lv['tp1']} (RR 2:1) | TP2 ${lv['tp2']} (3:1) | TP3 ${lv['tp3']} (4:1)")
    print("─" * 66)
    bar = "█" * int(c["score"]) + "░" * (10 - int(c["score"]))
    print(f"  🎯 CONFLUENCE  [{bar}]  {c['score']}/10  {c['direction']}  (alignés {c['aligned']})")
    if c["htf_conflict"]:
        print("  ⚠️ Conflit avec 1D (HTF) → conviction réduite")
    print(f"  {'✅ SIGNAL VALIDE' if c['score']>=THRESHOLDS['valid'] else ('👁️ WATCH' if c['score']>=THRESHOLDS['watch'] else '❌ NON')}, seuil trade {THRESHOLDS['valid']}")
    print("═" * 66)


if __name__ == "__main__":
    run_analysis(verbose=True)
