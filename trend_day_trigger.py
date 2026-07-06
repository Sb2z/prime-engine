#!/usr/bin/env python3
"""TREND DAY TRIGGER — détecteur du mode scalp-tendance.

L'edge documenté de Sam (LESSONS.md, 57 trades réels) : scalp des
micro-rebonds DANS LE SENS les jours de tendance propre (ADX>30, ER élevé).
Ce module détecte ces conditions en temps réel et alerte "conditions du
5 juin réunies" avec direction et zones de rebond.

GARDE-FOU D'HONNÊTETÉ (inclus dans chaque alerte) : l'échantillon de
référence est UN seul jour à 89% plus les stats agrégées ADX>30. C'est le
meilleur edge documenté du journal, mais il repose sur peu de jours
distincts → sizing NORMAL, jamais de doublement "parce que c'est LE jour".
Le forward-test dira en combien de jours de tendance propre il se confirme.

C'est l'inverse de Prime (swings RR>=2) : deux modes distincts, le régime
décide. Pendant Gate 1 les seuils Prime sont GELÉS, donc ce module est
purement additif (alerte) et ne supprime aucun A_SETUP.
"""

import datetime as dt

import calendar_feed
import datafeed
import regime
import tv_candles

ASSETS = ("GOLD", "US500")
ARM_ADX = 30.0
ARM_ER = 0.45


def _ta(candles):
    """Indicateurs TA sur une liste de bougies (réutilise tv_candles)."""
    if not candles or len(candles) < 30:
        return None
    return tv_candles.compute_ta(candles)


def _tf_direction(ta):
    """Direction d'un timeframe : close vs EMA50 + signe du MACD."""
    if not ta:
        return None
    up = (ta["close"] >= ta["ema50"]) + (ta["macd"] >= ta["macd_sig"])
    if up == 2:
        return "LONG"
    if up == 0:
        return "SHORT"
    return "NEUTRAL"


def check(asset):
    """Évalue les conditions d'armement pour un actif.

    Armé si : ADX 15m > 30, ER > 0.45 (régime TENDANCE PROPRE de regime.py),
    direction 15m alignée avec 1h, 4h pas opposé. Bonus signalé si EVENT_DAY.
    """
    # 150 barres : le seeding Wilder sur 60 barres portait ~2-3 pts de biais
    # ADX vs la référence (prouvé par le test de parité Pine du 10/06).
    # Correction de JUSTESSE approuvée par Sam (token 10/06), pas un seuil.
    c15 = datafeed.get_candles(asset, "15m", 150)
    c1h = datafeed.get_candles(asset, "1h", 100)
    if not c15 or c15.get("stale") or not c1h or c1h.get("stale"):
        return {"asset": asset, "armed": False, "reason": "données indisponibles"}
    ta15, ta1h = _ta(c15["candles"]), _ta(c1h["candles"])
    if not ta15 or not ta1h:
        return {"asset": asset, "armed": False, "reason": "TA incomplet"}

    rg = regime.detect(c15["candles"], adx=ta15["adx"])
    d15, d1h = _tf_direction(ta15), _tf_direction(ta1h)

    conditions = {
        "adx15_gt_30": ta15["adx"] > ARM_ADX,
        "er_gt_045": (rg.get("er") or 0) > ARM_ER,
        "direction_15m": d15,
        "aligne_1h": d15 != "NEUTRAL" and d15 == d1h,
    }
    armed = all([conditions["adx15_gt_30"], conditions["er_gt_045"],
                 conditions["aligne_1h"]])

    try:
        cal = calendar_feed.event_mode()
    except Exception:
        cal = {"mode": None}
    event_day = cal.get("mode") == "EVENT_DAY"

    out = {
        "asset": asset,
        "armed": armed,
        "direction": d15 if armed else None,
        "adx_15m": round(ta15["adx"], 1),
        "er": rg.get("er"),
        "regime": rg.get("regime"),
        "event_day": event_day,
        "event_detail": cal.get("detail") if event_day else None,
        "zones_rebond": {"ema20_15m": ta15["ema20"], "ema50_15m": ta15["ema50"]},
        "price": ta15["close"],
        "conditions": conditions,
    }
    if armed:
        out["message"] = alert_text(out)
    return out


def alert_text(state):
    d = state["direction"]
    sens = "shorts sur rebonds" if d == "SHORT" else "longs sur replis"
    z = state["zones_rebond"]
    lines = [
        f"🔥 MODE SCALP TENDANCE — {state['asset']} {d}",
        f"Conditions du 5 juin réunies : ADX15m {state['adx_15m']} (>30), "
        f"ER {state['er']} (>0.45), 15m/1h alignés. Régime {state['regime']}.",
        f"Prix {state['price']} · zones de rebond : EMA20 15m {z['ema20_15m']} / "
        f"EMA50 15m {z['ema50_15m']}.",
        f"Règles : {sens} UNIQUEMENT (sens de la tendance), sortie rapide, "
        f"stop ATR, pas de contre-tendance.",
    ]
    if state.get("event_day"):
        lines.append(f"⚡ EVENT DAY confirmé ({state['event_detail']}) — "
                     f"le profil du 5 juin avait aussi une surprise macro.")
    lines.append(
        "⚠️ Rappel échantillon : la référence = 1 SEUL jour à 89% + stats "
        "agrégées ADX>30 de tes 57 trades. SIZING NORMAL, pas de doublement "
        "— le forward-test dira si le pattern tient."
    )
    return "\n".join(lines)


def check_all():
    return [check(a) for a in ASSETS]


if __name__ == "__main__":
    for s in check_all():
        if s["armed"]:
            print(s["message"])
        else:
            print(f"{s['asset']}: pas armé — ADX15m {s.get('adx_15m')} ER {s.get('er')} "
                  f"regime {s.get('regime')} cond={s.get('conditions')}")
