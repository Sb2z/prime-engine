#!/usr/bin/env python3
"""
FORECAST, Anticipation de tendance multi-timeframe (15m / 1h / 4h)
══════════════════════════════════════════════════════════════════
NE donne PAS de trade (pas d'entrée/stop/TP). Donne la DIRECTION ANTICIPÉE
du cours par timeframe, à partir de TOUT le contexte : news, macro, technique,
order flow, structure, sentiment. Sam gère sa stratégie ; ceci est sa boussole.

Sortie par actif :
  15m → momentum immédiat + order flow + news qui tombent
  1h  → tendance intraday + macro de la séance + structure
  4h  → tendance de fond + fondamental + régime
"""

import news_radar


def _dirword(score):
    if score >= 0.6: return ("↗ HAUSSIER", "#16a34a")
    if score >= 0.2: return ("↗ légèrement haussier", "#65a30d")
    if score <= -0.6: return ("↘ BAISSIER", "#ef4444")
    if score <= -0.2: return ("↘ légèrement baissier", "#f97316")
    return ("↔ RANGE / indécis", "#9aa0a6")


def _tf_dir(ta):
    """Direction nette d'un timeframe depuis sa TA (-1..+1)."""
    if not ta or "error" in ta:
        return 0
    s = 0
    rsi = ta.get("rsi", 50); adx = ta.get("adx", 0)
    dip = ta.get("di_plus", 0); dim = ta.get("di_minus", 0)
    macd = ta.get("macd", 0); macds = ta.get("macd_sig", 0)
    close = ta.get("close", 0); ema20 = ta.get("ema20", close); ema50 = ta.get("ema50", close)
    s += 0.4 if macd > macds else -0.4
    if adx > 20:
        s += 0.4 if dip > dim else -0.4
    s += 0.2 if close > ema50 else -0.2
    if rsi > 68: s -= 0.15
    elif rsi < 32: s += 0.15
    return max(-1, min(1, s))


def forecast(asset="GOLD"):
    """Anticipation 15m/1h/4h pour un actif, avec les drivers."""
    if asset == "GOLD":
        import aurum
        R = aurum.run_analysis(verbose=False)
        macro = R.get("macro", {}).get("score", {})
        edge = R.get("edge", {})
    else:
        import sentinel500
        R = sentinel500.run_analysis(verbose=False)
        macro = R.get("macro", {}).get("score", {})
        edge = R.get("edge", {})
    ta = R.get("ta", {})
    of = R.get("orderflow", {})
    sm = R.get("smc", {})
    news = R.get("news", {})

    macro_dir = 1 if macro.get("direction") == "LONG" else (-1 if macro.get("direction") == "SHORT" else 0)
    macro_mag = min(abs(macro.get("score", 0)) / 3, 1)
    news_dir = 1 if news.get("direction") == "LONG" else (-1 if news.get("direction") == "SHORT" else 0)
    of_score = of.get("score", 0) or 0
    struct = sm.get("structure", "RANGE")
    struct_dir = 1 if struct == "UPTREND" else (-1 if struct == "DOWNTREND" else 0)

    d15 = _tf_dir(ta.get("15m"))
    d1h = _tf_dir(ta.get("1h"))
    d4h = _tf_dir(ta.get("4h"))
    d1d = _tf_dir(ta.get("1d"))

    # Composition par timeframe (poids différents selon l'horizon)
    f15 = 0.55 * d15 + 0.30 * (of_score / 1.5) + 0.15 * news_dir
    f1h = 0.45 * d1h + 0.25 * macro_dir * macro_mag + 0.15 * struct_dir + 0.15 * news_dir
    f4h = 0.40 * d4h + 0.25 * d1d + 0.20 * macro_dir * macro_mag + 0.15 * struct_dir

    # Caveat survente/surachat (mean reversion possible)
    stoch4 = (ta.get("4h", {}) or {}).get("stoch_k", 50)
    caveat = ""
    if stoch4 < 12:
        caveat = "⚠️ survente extrême 4H → rebond technique possible à court terme"
    elif stoch4 > 88:
        caveat = "⚠️ surachat extrême 4H → repli technique possible"

    # Source dégradée : prix indisponible OU >=2 des 3 TF intraday en erreur de
    # fetch. Sert au protocole à forcer NO_TRADE (jamais décider sur données mortes).
    ta_errors = sum(1 for k in ("15m", "1h", "4h") if "error" in (ta.get(k) or {}))
    price = R.get("price")
    return {"asset": asset, "price": price, "chg": R.get("chg"),
            "tf": {"15m": f15, "1h": f1h, "4h": f4h},
            "structure": struct, "regime": R.get("regime"),
            "macro": macro, "news": news, "orderflow": of, "edge": edge,
            "caveat": caveat,
            "price_source": R.get("price_source"),
            "source_degraded": (price is None) or (ta_errors >= 2),
            "drivers": _drivers(R)}


def _drivers(R):
    """Les forces qui poussent le cours (résumé contextuel)."""
    out = []
    ms = R.get("macro", {}).get("score", {})
    for n, txt, s in ms.get("signals", []):
        if s != 0:
            out.append(("🔴" if s < 0 else "🟢") + " " + txt)
    of = R.get("orderflow", {})
    for s in of.get("signals", [])[:2]:
        out.append(s)
    nb = R.get("news", {})
    fed = nb.get("context", {}).get("fundamental_bias", {}).get("fed_posture")
    if fed:
        out.append(f"📰 Posture Fed : {fed}")
    return out[:7]


def dual():
    """Anticipation GOLD + S&P avec le contexte News Radar."""
    rad = news_radar.radar()
    alert, amsg = news_radar._window_alert(rad)
    fg = rad.get("fear_greed") or {}
    g = forecast("GOLD")
    s = forecast("US500")
    return {"radar": {"alert": alert, "msg": amsg, "fg": fg,
                      "gold_bias": rad["gold_bias"], "spx_bias": rad["spx_bias"],
                      "top_news": rad["items"][:5]},
            "gold": g, "spx": s}


def _print_fc(f, label):
    print(f"\n  {label}  {f['price']} ({f.get('chg'):+.2f}%) · structure {f['structure']} · régime {f['regime']}")
    for tf in ("15m", "1h", "4h"):
        w, _ = _dirword(f["tf"][tf])
        bar = f["tf"][tf]
        arrows = "█" * int(abs(bar) * 10) + "░" * (10 - int(abs(bar) * 10))
        print(f"     {tf:4} [{arrows}] {w}")
    if f["caveat"]:
        print(f"     {f['caveat']}")
    print(f"     Drivers :")
    for d in f["drivers"]:
        print(f"        {d}")


if __name__ == "__main__":
    r = dual()
    rd = r["radar"]
    print("═" * 66)
    print(f"  🧭 ANTICIPATION DE TENDANCE, {__import__('datetime').datetime.now().strftime('%H:%M')}")
    print("═" * 66)
    print(f"  📡 Contexte news : {rd['alert']}, {rd['msg']}")
    print(f"  😱 Fear&Greed {rd['fg'].get('score','?')} ({rd['fg'].get('rating','')}) · biais news OR {rd['gold_bias']:+d} / S&P {rd['spx_bias']:+d}")
    _print_fc(r["gold"], "🥇 GOLD")
    _print_fc(r["spx"], "🛡️ S&P 500")
    print("═" * 66)
