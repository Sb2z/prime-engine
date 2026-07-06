#!/usr/bin/env python3
"""MARKET BRIEF — briefing de tendance plusieurs fois/jour (signal-only).

EN PLUS des alertes de trade/setup, envoie sur le même bot Telegram un point
de tendance par actif suivi (GOLD, US500), structuré en 3 lectures (Sam,
2026-06-13) :

  1. Tendance de FOND      → forecast 4h + régime (où va l'actif
                             structurellement, tendance de fond)
  2. Tendance JOURNALIÈRE  → forecast 1h intraday + variation du jour (où il
                             se dirige aujourd'hui pour l'instant)
  3. Tendance INTELLIGENTE → synthèse IA pondérée des 3 horizons (news, macro,
                             order flow, structure déjà intégrés par forecast)
                             + niveaux concrets : support/résistance (nuage
                             Ichimoku, haut/bas du jour) et range projeté (ATR)

LECTURE SEULE : appelle forecast.dual() (qui ne touche PAS DuckDB) et le feed
de bougies. N'écrit rien, ne verrouille rien — totalement découplé du watcher
de production. L'échec d'un calcul de niveaux n'empêche jamais l'envoi.
"""

import datetime as dt
import tz

import forecast

ATR_N = 14
CANDLE_TF = "1h"
CANDLE_N = 140


def _atr(candles, n=ATR_N):
    if len(candles) < n + 1:
        return None
    trs = []
    for i in range(len(candles) - n, len(candles)):
        h, l, pc = float(candles[i][2]), float(candles[i][3]), float(candles[i - 1][4])
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    a = sum(trs) / n
    return a if a > 0 else None


def _today_high_low(candles):
    """Plus haut / plus bas des bougies du jour (jour calendaire Paris)."""
    now_paris = tz.paris_now()
    midnight_paris = now_paris.replace(hour=0, minute=0, second=0, microsecond=0)
    start_epoch = midnight_paris.timestamp()
    today = [c for c in candles if c[0] >= start_epoch]
    if not today:
        return None, None
    return max(float(c[2]) for c in today), min(float(c[3]) for c in today)


def _levels(asset_sym, price):
    """Support/résistance (Ichimoku + haut/bas du jour) + range projeté ATR.

    Renvoie None proprement en cas de souci (le briefing part sans niveaux).
    """
    try:
        import datafeed
        import strategy_families as sf
        res = datafeed.get_candles(asset_sym, CANDLE_TF, CANDLE_N)
        candles = (res or {}).get("candles") or []
        if len(candles) < 90 or not price:
            return None
        st = sf.ichimoku_state(candles, "standard")
        atr = _atr(candles)
        dh, dl = _today_high_low(candles)
        cand = {}
        if st:
            cand["Kijun"] = st["kijun"]
            cand["haut nuage"] = st["cloud_top"]
            cand["bas nuage"] = st["cloud_bot"]
        if dh:
            cand["haut du jour"] = dh
        if dl:
            cand["bas du jour"] = dl
        above = sorted((v, k) for k, v in cand.items() if v > price)
        below = sorted(((v, k) for k, v in cand.items() if v < price), reverse=True)
        proj_hi = max([x for x in (dh, (price + atr) if atr else None) if x], default=None)
        proj_lo = min([x for x in (dl, (price - atr) if atr else None) if x], default=None)
        return {"support": below[0] if below else None,
                "resistance": above[0] if above else None,
                "proj_hi": proj_hi, "proj_lo": proj_lo}
    except Exception:
        return None


def _w(score):
    return forecast._dirword(score)[0]


def _strength(score):
    a = abs(score)
    if a >= 0.6:
        return "forte"
    if a >= 0.25:
        return "modérée"
    return "faible"


def _fmt(p):
    return "?" if p is None else f"{p:,.1f}".replace(",", " ")


def _asset_block(f):
    tf = f["tf"]
    # Synthèse IA : pondération vers le fond + l'intraday pour la suite du jour
    intel = 0.20 * tf["15m"] + 0.35 * tf["1h"] + 0.45 * tf["4h"]
    sym = f["asset"]
    emoji = "🥇" if sym == "GOLD" else "🛡️"
    name = "GOLD" if sym == "GOLD" else "S&P 500"
    chg = f.get("chg")
    chg_txt = f"{chg:+.2f}%" if chg is not None else "?"
    L = [f"{emoji} {name}  {_fmt(f.get('price'))} ({chg_txt}) · régime {f.get('regime')}"]
    L.append(f"  • Fond (4h)        : {_w(tf['4h'])}")
    L.append(f"  • Journalière (1h) : {_w(tf['1h'])}")
    L.append(f"  • IA (jour)        : {_w(intel)} · conviction {_strength(intel)}")
    if f.get("caveat"):
        L.append(f"    {f['caveat']}")
    lv = _levels(sym, f.get("price"))
    if lv:
        parts = []
        if lv["support"]:
            parts.append(f"support {_fmt(lv['support'][0])} ({lv['support'][1]})")
        if lv["resistance"]:
            parts.append(f"résistance {_fmt(lv['resistance'][0])} ({lv['resistance'][1]})")
        if parts:
            L.append("    Niveaux: " + " · ".join(parts))
        if lv["proj_lo"] and lv["proj_hi"]:
            L.append(f"    Range projeté jour: [{_fmt(lv['proj_lo'])} — {_fmt(lv['proj_hi'])}]")
    drv = f.get("drivers") or []
    if drv:
        L.append("    Drivers: " + " · ".join(drv[:2]))
    return "\n".join(L)


def build_brief():
    fc = forecast.dual()
    rd = fc["radar"]
    fg = rd.get("fg") or {}
    now_paris = tz.paris_now()
    weekend = " · ⚠️ week-end (marché fermé, lecture indicative)" if now_paris.weekday() >= 5 else ""
    head = [
        f"🧭 BRIEFING TENDANCE — {now_paris.strftime('%H:%M')}{weekend}",
        f"📡 {rd.get('alert', '')} · F&G {fg.get('score', '?')} ({fg.get('rating', '')}) "
        f"· biais news OR {rd.get('gold_bias', 0):+d} / S&P {rd.get('spx_bias', 0):+d}",
        "",
        _asset_block(fc["gold"]),
        "",
        _asset_block(fc["spx"]),
    ]
    return "\n".join(head)


def send_brief():
    import notify
    msg = build_brief()
    ok = notify.send(msg, silent=False)  # journée → sonore
    return ok, msg


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "print":
        print(build_brief())
    else:
        ok, msg = send_brief()
        print(msg)
        print("--- telegram:", "OK" if ok else "ÉCHEC")
