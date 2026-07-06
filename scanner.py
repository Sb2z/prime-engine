#!/usr/bin/env python3
"""
SCANNER — Détecteur de setups PROPRES à RR élevé (mode "pas scalp")
══════════════════════════════════════════════════════════════════
Quand le régime n'est PAS scalp-friendly (haché/range), on bascule en mode SETUP :
moins de trades, mais PROPRES — confluence totale (macro, news, options, SMC, order
flow) + entrée sur zone de confluence + RR ≥ 2. Objectif : 3-5 trades de qualité/jour.

Un setup PROPRE = confluence ≥ 6.5 + plusieurs couches alignées sur une ZONE
(OTE + OB + Fib + mur options + POC) + cible logique donnant RR ≥ 2.
Le scanner est ÉVOLUTIF : il re-tourne et s'adapte au contexte.
"""

import clusters
import costs

# RR : plus de cible RR FIXE obligatoire (demande Sam 2026-06-16 — « le but c'est
# le profit, un alliage intelligent, pas un RR fixe »). RR_MIN_SETUP n'est plus
# qu'un plancher de SANTÉ (le gain couvre au moins le risque, évite les loteries
# à skew négatif) ; le RR optimal par stratégie × régime pour MAXIMISER L'ESPÉRANCE
# nette de coûts est découvert par le juge, pas fixé ici. RR_TARGET_DEFAULT = TP de
# repli quand aucune cible logique n'existe. Plancher à affiner/lever par le lab.
RR_MIN_SETUP = 1.0
RR_TARGET_DEFAULT = 2.0
CONF_MIN = 6.5
STOP_ATR_FLOOR = 0.6      # stop minimum en multiple d'ATR15m (proxy clusters.ATR15M_PCT)
MAX_COST_SHARE = 0.15     # spread+slippage ne doivent pas dépasser 15% du stop
MAX_ENTRY_ATR = 1.5       # garde-fou (2026-06-16) : l'entrée annoncée ne peut être
#                           à plus de 1.5 x ATR15m du prix. L'entrée OTE (retracement
#                           0.705 du range du jour) tombait en médiane à ~1.3% du prix,
#                           du mauvais côté → jamais remplie en intraday sur jour de
#                           tendance (0% en 45 min, cf. diagnostic). On rapproche le repli
#                           à une distance atteignable (compatible momentum), à VALIDER
#                           finement par le juge (mode breakout/momentum par régime).
MAX_TP_ATR = 10.0         # plafond intraday (2026-06-16) : un TP au-delà de
#                           10 x ATR15m (~1.75% US500 / 2.0% GOLD) n'est pas
#                           atteignable en intraday. Les cibles venant des murs
#                           d'options / fibs du range du jour donnaient des TP à
#                           +3 à +7% (S&P 7800, GOLD 4632). On borne ; les bons TP
#                           (~+1.55%) passent inchangés. Valeur à affiner par le juge.
STOP_CAP_ATR = 2.0        # quand l'entrée est rapprochée (cap), le stop devient
#                           une invalidation volatilité (2 x ATR15m) depuis la
#                           nouvelle entrée — pas la distance OTE recopiée (P3).
TREND_ENTRY_ATR = 0.0     # (2026-06-22) offset d'entrée en TENDANCE-continuation, en
#                           multiple d'ATR15m : 0 = AU MARCHÉ. En tendance technique
#                           propre, le repli OTE (MAX_ENTRY_ATR) n'imprime quasi jamais
#                           dans la fenêtre de 45 min → 67% de NOFILL sur GOLD (6/9, le
#                           seul actif où Sam fait son argent). On entre alors au marché
#                           pour PARTICIPER ; range/transition gardent MAX_ENTRY_ATR (le
#                           repli s'y remplit, US500 100%). Lever de FILL pur (ne touche
#                           ni CONF_A ni RR). Knob à optimiser par le juge (0 vs offset+).
TREND_ENTRY_H = (14, 23)  # (2026-07-02) fenêtre Paris où l'entrée-marché est permise
#                           (session NY) — hors fenêtre, retour au repli OTE limite.


def _paris_hour():
    """Heure murale Paris (int). Isolée pour être monkeypatchable dans les tests."""
    import tz
    return tz.paris_now().hour


def _collect_targets(R, direction):
    """Niveaux logiques de cible dans le sens du trade (options, POC, Fib, VAL/VAH)."""
    price = R.get("price")
    lv = []
    op = R.get("options") or {}
    of = R.get("orderflow") or {}
    fibs = R.get("fibs") or {}
    cands = []
    for v in (op.get("max_pain_u") or op.get("max_pain"), op.get("put_wall_u") or op.get("put_wall"),
              op.get("call_wall_u") or op.get("call_wall"), of.get("poc"), of.get("vah"), of.get("val")):
        if v: cands.append(v)
    for v in (fibs or {}).values():
        if isinstance(v, (int, float)): cands.append(v)
    for c in cands:
        if direction == "LONG" and c > price:
            lv.append(c)
        elif direction == "SHORT" and c < price:
            lv.append(c)
    lv.sort(reverse=(direction == "SHORT"))
    return lv


def quality_setup(R, asset):
    """Construit le meilleur setup propre pour un actif, ou None."""
    conf = R.get("confluence", {})
    score = conf.get("score", 0)
    direction = conf.get("direction")
    if score < CONF_MIN or direction not in ("LONG", "SHORT"):
        return None
    strat = R.get("strategy") or {}
    lv = strat.get("levels") or {}
    ote = strat.get("ote") or {}
    if not lv:
        return None
    entry = ote.get("sweet_spot") or lv.get("entry")
    stop = lv.get("stop")
    if not entry or not stop:
        return None
    sign = 1 if direction == "LONG" else -1

    # ── GARDE-FOU DE DISTANCE D'ENTRÉE (2026-06-16) ──────────────────────────
    # Si l'entrée OTE est trop loin du prix (repli profond injoignable en
    # intraday), on la ramène à MAX_ENTRY_ATR x ATR15m du prix, DU MÊME CÔTÉ.
    # Le stop est alors recalculé comme une INVALIDATION VOLATILITÉ (STOP_CAP_ATR
    # x ATR15m) depuis la NOUVELLE entrée — PAS en recopiant la distance OTE
    # d'origine, qui supposait un repli profond inexistant (audit 2026-06-17, P3).
    # Le plancher de stop/coûts et le RR ci-dessous restent appliqués ensuite.
    entry_capped = False
    price = R.get("price")
    if price:
        atr15m_p = price * clusters.ATR15M_PCT.get(asset, 0.20) / 100
        # Cap d'entrée RÉGIME-CONSCIENT (2026-06-22) : en TENDANCE technique (régime de
        # continuation), on entre AU MARCHÉ (TREND_ENTRY_ATR≈0) car le repli OTE ne vient
        # pas dans la fenêtre (67% NOFILL GOLD) ; sinon on garde le repli MAX_ENTRY_ATR.
        # Source = régime TECHNIQUE (regime_scalp), PAS le régime macro R["regime"] (MIXED…).
        tregime = (R.get("regime_scalp") or {}).get("regime") or ""
        trend_cont = ("TENDANCE PROPRE" in tregime) or ("TENDANCE MOYENNE" in tregime)
        # Garde-fou (audit 2026-07-02) : l'entrée-marché est LIMITÉE à la fenêtre
        # NY (14h-23h Paris). Mesuré post-fix : 6 fills marché hors-NY = 6 pertes
        # (-2.19%), extension nocturne + spread off-session 2.4x ; en NY le seul
        # fill marché a gagné. Hors NY on revient au repli OTE limite (au pire
        # NOFILL = gratuit). Le fix 22/06 n'étant pas prouvé, on borne son risque.
        trend_cont = trend_cont and (TREND_ENTRY_H[0] <= _paris_hour() < TREND_ENTRY_H[1])
        cap = (TREND_ENTRY_ATR if trend_cont else MAX_ENTRY_ATR) * atr15m_p
        pull = price - entry            # >0 : entrée sous le prix (repli LONG)
        if abs(pull) > cap:
            entry = round(price, 2) if cap <= 0 else round(price - (cap if pull > 0 else -cap), 2)
            stop = round(entry - sign * STOP_CAP_ATR * atr15m_p, 2)
            entry_capped = True

    risk = abs(entry - stop)
    if risk <= 0:
        return None
    # Plancher de stop : un stop plus serré que 0.6 x ATR15m OU dont les coûts
    # (spread+slippage) mangent plus de 15% est dans le bruit du spread
    # (A_SETUP du 9 juin : 8 points sur US500). On élargit et on recalcule le
    # RR ; si le RR retombe sous 2, le setup est rejeté plus bas.
    stop_widened = False
    atr15m = entry * clusters.ATR15M_PCT.get(asset, 0.20) / 100
    cost_floor = (costs.spread_points(asset, "SESSION", entry)
                  + costs.slippage_points(asset, entry)) / MAX_COST_SHARE
    floor = max(STOP_ATR_FLOOR * atr15m, cost_floor)
    if risk < floor:
        stop = round(entry - sign * floor, 2)
        risk = abs(entry - stop)
        stop_widened = True
    # Cible : le 1er niveau logique au-dessus du plancher de santé ; sinon le plus
    # loin ; sinon un TP de repli RR_TARGET_DEFAULT. Le RR n'est plus imposé à 2 :
    # il découle de la cible logique du contexte (le juge optimisera la politique).
    targets = _collect_targets(R, direction)
    tp = None
    for t in targets:
        if abs(t - entry) / risk >= RR_MIN_SETUP:
            tp = t; break
    if tp is None and targets:
        tp = targets[-1]
    if tp is None:
        tp = round(entry + sign * RR_TARGET_DEFAULT * risk, 2)
    # Plafond intraday du TP : au-delà de MAX_TP_ATR x ATR15m la cible (mur
    # d'options / fib du range du jour) n'est pas atteignable dans l'horizon
    # intraday. On la ramène ; RR>=2 reste exigé ci-dessous.
    tp_capped = False
    max_tp = MAX_TP_ATR * atr15m
    if abs(tp - entry) > max_tp:
        tp = round(entry + sign * max_tp, 2)
        tp_capped = True
    rr = round(abs(tp - entry) / risk, 2)
    if rr < RR_MIN_SETUP:
        return None

    # Compter les couches alignées (qualité de confluence)
    aligned = conf.get("aligned", "?")
    rg = R.get("regime_scalp") or {}
    strat_name = (R.get("strategy") or {}).get("name")
    return {"asset": asset, "direction": direction, "conf": score, "aligned": aligned,
            "entry": round(entry, 2), "stop": round(stop, 2), "tp": round(tp, 2), "rr": rr,
            "stop_widened": stop_widened, "entry_capped": entry_capped,
            "tp_capped": tp_capped,
            # mode d'entrée effectif -> journalisé par log_pending_setup pour
            # rendre le fill ATTRIBUABLE au mécanisme (audit 07-02) :
            # MARKET_TREND = entrée-marché tendance (fix 22/06, fenêtre NY),
            # OTE_CAPPED = repli rapproché au cap, OTE = repli intact.
            "entry_mode": ("MARKET_TREND" if (entry_capped and trend_cont)
                           else "OTE_CAPPED" if entry_capped else "OTE"),
            "regime": rg.get("regime"), "strategy": strat_name, "drivers": _drivers(R)}


def _drivers(R):
    out = []
    ms = R.get("macro", {}).get("score", {})
    for n, txt, s in ms.get("signals", []):
        if s != 0:
            out.append(("🔴" if s < 0 else "🟢") + " " + txt)
    op = R.get("options")
    if op:
        out.append(f"🎰 Max Pain {op.get('max_pain_u') or op.get('max_pain')} · régime {op.get('gex_regime','')[:18]}")
    return out[:5]


def scan():
    setups = []
    regimes = {}
    for asset in ("GOLD", "US500"):
        try:
            if asset == "GOLD":
                import aurum
                R = aurum.run_analysis(verbose=False)
            else:
                import sentinel500
                R = sentinel500.run_analysis(verbose=False)
        except Exception:
            continue
        regimes[asset] = R.get("regime_scalp") or {}
        s = quality_setup(R, asset)
        if s:
            setups.append(s)
    setups.sort(key=lambda x: (x["conf"], x["rr"]), reverse=True)
    return {"setups": setups, "regimes": regimes}


if __name__ == "__main__":
    r = scan()
    print("═" * 64)
    print("  🎯 SCANNER SETUPS PROPRES (mode qualité, RR ≥ 2)")
    print("═" * 64)
    for a, rg in r["regimes"].items():
        mode = "SCALP" if rg.get("scalp_ok") else "SETUP (pas scalp)"
        print(f"  {a}: régime {rg.get('regime','?')} → mode {mode}")
    if not r["setups"]:
        print("\n  ⏳ Aucun setup propre (confluence<6.5 ou RR<2) — on ATTEND. Patience = qualité.")
    else:
        for s in r["setups"]:
            print(f"\n  {'🟢' if s['direction']=='LONG' else '🔴'} {s['asset']} {s['direction']} — confluence {s['conf']}/10 (alignés {s['aligned']})")
            print(f"     Entrée {s['entry']} · Stop {s['stop']} · TP {s['tp']} · RR {s['rr']}:1")
            for d in s["drivers"]:
                print(f"     {d}")
    print("═" * 64)
