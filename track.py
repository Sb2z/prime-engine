#!/usr/bin/env python3
"""
TRACK — Runner du journal auto-apprenant
══════════════════════════════════════════════════════════════════
Pipeline complet à chaque scan :
  1. Fetch prix T0 (WebSocket) + TA 1H (WebSocket) pour tous les actifs
  2. Évalue les signaux OUVERTS du journal contre le prix réel (TP/Stop/MFE/MAE)
  3. Logge les nouveaux signaux directionnels (score >= seuil)
  4. Affiche la performance réelle accumulée + modificateurs de confiance appris

Usage : python3 track.py
"""

import datetime
import tz
from tv_live    import TVLiveClient
from tv_candles import TVCandleClient, SYMBOL_MAP
import journal

# SENTINEL-500 : focus S&P 500. GOLD ajouté pour évaluer les trades AURUM.
# NAS100/VIX/DXY = contexte macro.
TRADE_ASSETS = ["US500"]
CONTEXT      = ["GOLD", "NAS100", "VIX", "DXY"]
LOG_THRESHOLD = 6.0   # on logge tout signal directionnel >= 6 pour bâtir la donnée


def paris_now():
    return tz.paris_now()


def convergence_score(buy, sell, adx):
    total = buy + sell
    if total == 0:
        return 0, "NEUTRAL"
    bull = buy / total * 7
    adx_bonus = 3 if adx > 35 else (2 if adx > 25 else (1 if adx > 15 else 0))
    long_score = round(min(bull + adx_bonus, 10), 1)
    # score directionnel : si buy>sell c'est un score LONG, sinon on calcule le SHORT
    if buy > sell:
        return long_score, "LONG"
    elif sell > buy:
        bear = sell / total * 7
        return round(min(bear + adx_bonus, 10), 1), "SHORT"
    return long_score, "NEUTRAL"


def current_session():
    h = paris_now().hour
    if 1 <= h < 9:   return "ASIAN"
    if 9 <= h < 14:  return "LONDON"
    if 14 <= h < 15: return "OVERLAP"
    if 15 <= h < 20: return "NY"
    if 20 <= h < 22: return "NY_CLOSE"
    return "CLOSED"


def main():
    ts = paris_now().strftime("%H:%M:%S")
    print(f"\n{'═'*66}")
    print(f"  📓 TRACK — Journal auto-apprenant — {ts} Paris")
    print(f"{'═'*66}")

    # 1. Prix T0
    all_syms = [SYMBOL_MAP[a] for a in TRADE_ASSETS + CONTEXT]
    raw = TVLiveClient(symbols=all_syms, timeout=16).fetch()

    # raw indexé par le ticker court (dernier segment) ; on remappe vers nos noms
    prices = {}
    for name in TRADE_ASSETS + CONTEXT:
        short = SYMBOL_MAP[name].split(":")[-1]
        if short in raw:
            prices[name] = raw[short]

    vix = prices.get("VIX", {}).get("lp")
    dxy = prices.get("DXY", {}).get("lp")
    session = current_session()

    # 2. Évalue les signaux ouverts AVANT de logger les nouveaux
    # (fills intrabar : bougies 1m pour voir les mèches entre deux scans)
    closed = journal.evaluate_open_live(prices=prices)
    if closed:
        print(f"\n  🔔 {len(closed)} signal(aux) clôturé(s) ce cycle :")
        for s in closed:
            icon = "✅" if s["result"].startswith("WIN") else ("❌" if s["result"].startswith("LOSS") else "➖")
            print(f"     {icon} {s['asset']} {s['direction']} @{s['entry']} → {s['result']} "
                  f"({s['pnl_pct']:+.2f}%)  [ouvert le {s['paris']}]")

    # 3. TA 1H + log des nouveaux signaux
    ta_all = TVCandleClient(symbols=TRADE_ASSETS, timeframe="1h", timeout=28).fetch_ta()

    print(f"\n  📊 SIGNAUX COURANTS (session {session})")
    logged = []
    for name in TRADE_ASSETS:
        d = ta_all.get(name, {})
        if "error" in d:
            print(f"     {name:7} ⚠️  {d['error']}")
            continue
        score, direc = convergence_score(d["buy"], d["sell"], d["adx"])
        lp = prices.get(name, {}).get("lp")
        mod, reason = journal.confidence_modifier(name, score, session, d["adx"])
        adj = round(score + mod, 1)

        # ── FILTRE ANTI-FADE (leçon journal 29/05) ──
        # Ne jamais fader une tendance forte : SHORT en uptrend ou LONG en downtrend
        # avec ADX>35 = squeeze quasi garanti. On bloque le log de ces signaux.
        ema50 = d.get("ema50") or d.get("close")
        close = d.get("close")
        trend_up = close is not None and ema50 is not None and close >= ema50
        counter_trend = (direc == "SHORT" and trend_up) or (direc == "LONG" and not trend_up)
        no_fade = counter_trend and d["adx"] > 35

        flag = ""
        if no_fade:
            flag = " ⛔ ANTI-FADE (ADX fort, contre-tendance — non loggé)"
        elif direc != "NEUTRAL" and score >= LOG_THRESHOLD and lp:
            sid = journal.log_signal(name, lp, direc, score, d, session, vix, dxy)
            if sid:
                logged.append((name, direc, score))
                flag = " 📝 loggé"
        modtxt = f"  conf{mod:+.1f}" if mod else ""
        print(f"     {name:7} {direc:7} {score:4.1f}/10{modtxt}  "
              f"RSI={d['rsi']:5.1f} ADX={d['adx']:5.1f} StochK={d['stoch_k']:5.1f}{flag}")
        if mod and reason != "neutre":
            print(f"             ↳ apprentissage: {reason}")

    # 4. Performance accumulée
    print(f"\n{journal.performance_report()}")
    print(f"{'═'*66}\n")


if __name__ == "__main__":
    main()
