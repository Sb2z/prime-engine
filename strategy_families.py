#!/usr/bin/env python3
"""STRATEGY FAMILIES — bibliothèque de signaux partagée juge/production.

SOURCE UNIQUE : le harness (backtest) et le watcher (shadow PAPER) évaluent
les stratégies via build_signal(family, params) — le même code des deux
côtés, donc aucun écart backtest/production possible par construction.

Le chercheur autonome compose des stratégies en CHOISISSANT famille +
paramètres. Ajouter une nouvelle famille = modifier ce fichier = token
humain requis (fichier protégé par le hook constitutionnel).

Interface d'un signal :
  fn(window, ctx=None) -> "LONG" | "SHORT" | None
  window : liste de bougies [ts, o, h, l, c, v] se terminant à la bougie de
           décision (close connue). AUCUN accès au futur : l'entrée se fait
           à l'open de la bougie suivante (géré par le harness/shadow).
  ctx    : dict optionnel (session, cot_pctile, event_mode...) — peut être
           absent, les familles doivent dégrader proprement.
"""

import datetime as dt
import tz


def _paris_hour(ts_epoch):
    return tz.to_paris(dt.datetime.fromtimestamp(ts_epoch, dt.timezone.utc)).hour


def _ret_pct(window, k):
    if len(window) < k + 1:
        return None
    a, b = float(window[-1 - k][4]), float(window[-1][4])
    return (b - a) / a * 100 if a else None


def _momentum(params):
    k = int(params.get("k", 4))
    thr = float(params.get("thr_pct", 0.3))

    def fn(window, ctx=None):
        r = _ret_pct(window, k)
        if r is None:
            return None
        if r > thr:
            return "LONG"
        if r < -thr:
            return "SHORT"
        return None
    return fn


def _mean_reversion(params):
    k = int(params.get("k", 4))
    thr = float(params.get("thr_pct", 0.5))

    def fn(window, ctx=None):
        r = _ret_pct(window, k)
        if r is None:
            return None
        if r > thr:
            return "SHORT"
        if r < -thr:
            return "LONG"
        return None
    return fn


def _session_hour(params):
    start = int(params.get("start", 15))
    end = int(params.get("end", 17))
    direction = params.get("direction", "LONG")

    def fn(window, ctx=None):
        h = _paris_hour(float(window[-1][0]))
        in_win = start <= h < end if start < end else (h >= start or h < end)
        return direction if in_win else None
    return fn


def _er_kaufman(closes, n=39):
    """Efficiency Ratio (même formule que regime.efficiency_ratio)."""
    if len(closes) < n + 1:
        return None
    net = abs(closes[-1] - closes[-1 - n])
    path = sum(abs(closes[i] - closes[i - 1]) for i in range(len(closes) - n, len(closes)))
    return net / path if path else 0.0


def _wilder_adx(window, n=14):
    """ADX Wilder autosuffisant (pas de dépendance non protégée)."""
    if len(window) < 2 * n + 1:
        return None
    highs = [float(c[2]) for c in window]
    lows = [float(c[3]) for c in window]
    closes = [float(c[4]) for c in window]
    trs, pdms, mdms = [], [], []
    for i in range(1, len(window)):
        trs.append(max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]),
                       abs(lows[i] - closes[i - 1])))
        up, dn = highs[i] - highs[i - 1], lows[i - 1] - lows[i]
        pdms.append(up if up > dn and up > 0 else 0.0)
        mdms.append(dn if dn > up and dn > 0 else 0.0)
    # Lissage Wilder
    atr, pdi_s, mdi_s = sum(trs[:n]), sum(pdms[:n]), sum(mdms[:n])
    dxs = []
    for i in range(n, len(trs)):
        atr = atr - atr / n + trs[i]
        pdi_s = pdi_s - pdi_s / n + pdms[i]
        mdi_s = mdi_s - mdi_s / n + mdms[i]
        if atr <= 0:
            continue
        pdi, mdi = 100 * pdi_s / atr, 100 * mdi_s / atr
        if pdi + mdi > 0:
            dxs.append(100 * abs(pdi - mdi) / (pdi + mdi))
    if len(dxs) < n:
        return None
    adx = sum(dxs[:n]) / n
    for x in dxs[n:]:
        adx = (adx * (n - 1) + x) / n
    return adx


def _momentum_regime(params):
    """Momentum CONDITIONNEL au régime de tendance propre (ER + ADX).

    Famille approuvée par Sam le 10/06/2026 (backlog run n°1) : teste si
    l'edge trend-day (momentum quand ER>seuil et ADX>seuil) se généralise.
    """
    k = int(params.get("k", 4))
    thr = float(params.get("thr_pct", 0.3))
    er_min = float(params.get("er_min", 0.45))
    adx_min = float(params.get("adx_min", 30.0))
    er_n = int(params.get("er_n", 39))
    adx_n = int(params.get("adx_n", 14))

    def fn(window, ctx=None):
        r = _ret_pct(window, k)
        if r is None:
            return None
        closes = [float(c[4]) for c in window]
        er = _er_kaufman(closes, er_n)
        adx = _wilder_adx(window, adx_n)
        if er is None or adx is None or er < er_min or adx < adx_min:
            return None
        if r > thr:
            return "LONG"
        if r < -thr:
            return "SHORT"
        return None
    return fn


def _cot_extreme(params):
    lo = float(params.get("lo_pctile", 10))
    hi = float(params.get("hi_pctile", 90))
    mode = params.get("mode", "contrarian")  # contrarian | follow

    def fn(window, ctx=None):
        p = (ctx or {}).get("cot_pctile")
        if p is None:
            return None
        if p <= lo:
            return "LONG" if mode == "contrarian" else "SHORT"
        if p >= hi:
            return "SHORT" if mode == "contrarian" else "LONG"
        return None
    return fn


# ── ICHIMOKU — périmètre FERMÉ (approuvé par Sam le 11/06/2026) ──────────────
# 5 signaux canoniques, 2 vitesses autorisées, AUCUN autre paramètre libre :
# le data mining de variantes est structurellement impossible dans ce fichier.
#
# ANTI-LOOKAHEAD PAR CONSTRUCTION : sur un graphique, Senkou A/B sont tracés
# `disp` bougies DEVANT le prix. Le nuage visible au-dessus de la bougie t a
# donc été calculé sur les données de t-disp. Ici, toute valeur "connue à t"
# est calculée via un décalage explicite (shift + disp) — jamais les
# midpoints du moment, qui décriraient le nuage de t+disp (le bug classique
# qui fabrique de faux edges). Chikou : comparer close(t) au high/low de
# t-disp n'utilise que du passé. Prouvé par test_ichimoku.py.

_ICHI_SPEEDS = {"standard": (9, 26, 52, 26), "fast": (7, 22, 44, 22)}


def _donchian_mid(window, n, shift=0):
    """(plus haut + plus bas) / 2 des n bougies se terminant shift barres avant t."""
    end = len(window) - shift
    start = end - n
    if start < 0 or end <= start:
        return None
    seg = window[start:end]
    return (max(float(c[2]) for c in seg) + min(float(c[3]) for c in seg)) / 2.0


def ichimoku_state(window, speed="standard", max_twist_age=60):
    """Toutes les valeurs Ichimoku CONNUES à la clôture de window[-1].

    Source unique juge/production/feature-store. Retourne None si la fenêtre
    est trop courte. Clés : tenkan, kijun, senkou_a, senkou_b, cloud_top,
    cloud_bot, prev (mêmes clés à t-1), close, prev_close, chikou (+1 close>
    high(t-disp), -1 close<low(t-disp), 0 sinon), twist_age (barres depuis le
    dernier changement de couleur du nuage connu, plafonné).
    """
    tk_n, kj_n, sb_n, disp = _ICHI_SPEEDS.get(speed, _ICHI_SPEEDS["standard"])
    if len(window) < sb_n + disp + 2:
        return None

    def lines(shift):
        tenkan = _donchian_mid(window, tk_n, shift)
        kijun = _donchian_mid(window, kj_n, shift)
        tk_p = _donchian_mid(window, tk_n, shift + disp)
        kj_p = _donchian_mid(window, kj_n, shift + disp)
        sa = (tk_p + kj_p) / 2.0 if tk_p is not None and kj_p is not None else None
        sb = _donchian_mid(window, sb_n, shift + disp)
        return tenkan, kijun, sa, sb

    def pack(shift):
        tenkan, kijun, sa, sb = lines(shift)
        if None in (tenkan, kijun, sa, sb):
            return None
        return {"tenkan": tenkan, "kijun": kijun, "senkou_a": sa, "senkou_b": sb,
                "cloud_top": max(sa, sb), "cloud_bot": min(sa, sb)}

    now, prev = pack(0), pack(1)
    if now is None or prev is None:
        return None

    close = float(window[-1][4])
    prev_close = float(window[-2][4])
    ref = window[len(window) - 1 - disp]
    chikou = 1 if close > float(ref[2]) else (-1 if close < float(ref[3]) else 0)

    sign0 = 1 if now["senkou_a"] >= now["senkou_b"] else -1
    twist_age = max_twist_age
    for shift in range(1, max_twist_age + 1):
        _, _, sa_s, sb_s = lines(shift)
        if sa_s is None or sb_s is None:
            break
        if (1 if sa_s >= sb_s else -1) != sign0:
            twist_age = shift
            break

    return dict(now, prev=prev, close=close, prev_close=prev_close,
                chikou=chikou, twist_age=twist_age)


def _ichimoku_tk_cross(params):
    """Croisement Tenkan/Kijun filtré par la position vs nuage."""
    speed = params.get("speed", "standard")

    def fn(window, ctx=None):
        s = ichimoku_state(window, speed)
        if s is None:
            return None
        d_now = s["tenkan"] - s["kijun"]
        d_prev = s["prev"]["tenkan"] - s["prev"]["kijun"]
        if d_prev <= 0 < d_now and s["close"] > s["cloud_top"]:
            return "LONG"
        if d_prev >= 0 > d_now and s["close"] < s["cloud_bot"]:
            return "SHORT"
        return None
    return fn


def _ichimoku_kumo_break(params):
    """Clôture qui sort du nuage (cassure du bord, connue à t)."""
    speed = params.get("speed", "standard")

    def fn(window, ctx=None):
        s = ichimoku_state(window, speed)
        if s is None:
            return None
        if s["prev_close"] <= s["prev"]["cloud_top"] and s["close"] > s["cloud_top"]:
            return "LONG"
        if s["prev_close"] >= s["prev"]["cloud_bot"] and s["close"] < s["cloud_bot"]:
            return "SHORT"
        return None
    return fn


def _ichimoku_kijun_reject(params):
    """Pullback qui touche Kijun et clôture du bon côté, en tendance nuage."""
    speed = params.get("speed", "standard")

    def fn(window, ctx=None):
        s = ichimoku_state(window, speed)
        if s is None:
            return None
        low, high = float(window[-1][3]), float(window[-1][2])
        if s["close"] > s["cloud_top"] and low <= s["kijun"] < s["close"]:
            return "LONG"
        if s["close"] < s["cloud_bot"] and high >= s["kijun"] > s["close"]:
            return "SHORT"
        return None
    return fn


def _ichimoku_twist(params):
    """Twist du nuage connu à t (changement de couleur), prix déjà du bon côté."""
    speed = params.get("speed", "standard")

    def fn(window, ctx=None):
        s = ichimoku_state(window, speed)
        if s is None or s["twist_age"] != 1:
            return None
        if s["close"] > s["cloud_top"]:
            return "LONG"
        if s["close"] < s["cloud_bot"]:
            return "SHORT"
        return None
    return fn


def _ichimoku_chikou_confirm(params):
    """Triple confirmation : Chikou dégagée + prix vs nuage + Tenkan vs Kijun."""
    speed = params.get("speed", "standard")

    def fn(window, ctx=None):
        s = ichimoku_state(window, speed)
        if s is None:
            return None
        if s["chikou"] == 1 and s["close"] > s["cloud_top"] and s["tenkan"] > s["kijun"]:
            return "LONG"
        if s["chikou"] == -1 and s["close"] < s["cloud_bot"] and s["tenkan"] < s["kijun"]:
            return "SHORT"
        return None
    return fn


def _momentum_breakout(params):
    """ENTRÉE-MARCHÉ SUR CASSURE en régime tendanciel (thèse momentum de Sam,
    famille approuvée par token 2026-06-17 ; spec analyste du 13/06).

    Cassure (style Donchian) du plus-haut / plus-bas des `lookback` bougies
    ANTÉRIEURES, CONFIRMÉE par une tendance propre (ER≥er_min ET ADX≥adx_min) :
    la clôture qui franchit le canal déclenche une entrée DANS le sens de la
    cassure. C'est l'opposé d'OTE_RETRACEMENT (qui attend un repli profond et
    rate les jours de tendance) — ici on suit le momentum.

    ANTI-LOOKAHEAD : le canal de référence EXCLUT la bougie de décision
    (window[-1-n:-1]) ; seule la clôture connue window[-1] est comparée. L'entrée
    réelle se fait à l'open de la bougie suivante (géré par le harness/shadow).
    Aucun accès au futur.
    """
    n = int(params.get("lookback", 20))
    er_min = float(params.get("er_min", 0.45))
    adx_min = float(params.get("adx_min", 30.0))
    er_n = int(params.get("er_n", 39))
    adx_n = int(params.get("adx_n", 14))

    def fn(window, ctx=None):
        if len(window) < max(n + 2, er_n + 1, 2 * adx_n + 1):
            return None
        closes = [float(c[4]) for c in window]
        er = _er_kaufman(closes, er_n)
        adx = _wilder_adx(window, adx_n)
        if er is None or adx is None or er < er_min or adx < adx_min:
            return None  # pas de tendance propre → aucune cassure jouable
        prior = window[-1 - n:-1]            # canal des n bougies AVANT la décision
        prior_high = max(float(c[2]) for c in prior)
        prior_low = min(float(c[3]) for c in prior)
        close = closes[-1]
        if close > prior_high:
            return "LONG"
        if close < prior_low:
            return "SHORT"
        return None
    return fn


FAMILIES = {
    "momentum": _momentum,
    "mean_reversion": _mean_reversion,
    "session_hour": _session_hour,
    "cot_extreme": _cot_extreme,
    "momentum_regime": _momentum_regime,
    "momentum_breakout": _momentum_breakout,
    "ichimoku_tk_cross": _ichimoku_tk_cross,
    "ichimoku_kumo_break": _ichimoku_kumo_break,
    "ichimoku_kijun_reject": _ichimoku_kijun_reject,
    "ichimoku_twist": _ichimoku_twist,
    "ichimoku_chikou_confirm": _ichimoku_chikou_confirm,
}


def build_signal(family, params):
    if family not in FAMILIES:
        raise ValueError(f"famille inconnue: {family} (disponibles: {sorted(FAMILIES)})")
    return FAMILIES[family](params or {})


if __name__ == "__main__":
    import json
    print("familles:", sorted(FAMILIES))
    fn = build_signal("momentum", {"k": 3, "thr_pct": 0.2})
    demo = [[i * 60, 100, 101, 99, 100 + i * 0.1, 0] for i in range(10)]
    print("momentum sur série montante:", fn(demo))
