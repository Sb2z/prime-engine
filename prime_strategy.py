#!/usr/bin/env python3
"""
PRIME STRATEGY — protocole remplaçant la stratégie discrétionnaire.
══════════════════════════════════════════════════════════════════
Objectif : privilégier ce que le journal montre comme supérieur :
  • setups OTE / continuation, RR >= 2
  • confluence élevée, SMC avec structure, order flow et macro alignés
  • éviter le scalp en régime haché/range et les breakouts chassés

Ce module ne passe aucun ordre. Il sort A_SETUP, WATCH ou NO_TRADE avec les
niveaux conditionnels. Les trades réels restent à confirmer/exécuter par Sam.
"""

import datetime
import json

import forecast
import adaptive_edge
import clusters
import journal
import news_radar
import position_policy
import scanner
import uncertainty

CONF_A = 7.0
CONF_B = 6.5
# Plus de RR FIXE obligatoire (demande Sam 2026-06-16 : « le but c'est le profit,
# un alliage intelligent, pas un RR fixe »). Le grade A n'est plus gardé par un seuil
# RR rigide mais par un GARDE-FOU D'ESPÉRANCE (cf. _expectancy_ok), décision Sam 2026-06-18 :
#  • RR_A_MIN : plancher de SANTÉ minimal absolu (en-dessous -> WATCH, jamais NO_TRADE
#    sur le seul RR).
#  • Si la stratégie a un historique suffisant (>= MIN_EXP_SAMPLE trades effectifs),
#    on exige son espérance nette historique >= 0 (le but c'est le profit, pas un RR).
#    Sinon (cold start, pas d'estimation fiable) on retombe sur un PRIOR RR prudent
#    (RR_A_PRIOR). adaptive_edge reste un filtre SUPPLÉMENTAIRE quand il est ACTIVE_FILTER,
#    mais ne note jamais le RR ni l'espérance -> ce n'est PAS lui le garde-fou (audit 06-18).
#  • RR_MAX_SANITY : au-delà, le RR vient d'un stop microscopique (bruit de
#    microstructure) ou d'un TP injoignable -> artefact, pas un edge.
RR_A_MIN = 1.2
RR_A_PRIOR = 1.5
RR_MAX_SANITY = 8.0
MIN_EXP_SAMPLE = 10   # trades EFFECTIFS mini pour se fier à l'espérance d'une stratégie
MIN_OTE_SAMPLE = 15  # trades EFFECTIFS (post-dédup), pas signaux bruts


def _stats_for(strategy=None, trader=None, direction=None):
    # Source unique : trades effectifs (doublons IA exclus, cf. clusters.py)
    closed = clusters.effective_trades()
    if strategy:
        closed = [t for t in closed if t.get("strategy") == strategy]
    if trader:
        closed = [
            t for t in closed
            if (t.get("trader") or ("USER" if t.get("source") == "REAL_TRADE" else "AI")) == trader
        ]
    if direction:
        closed = [t for t in closed if t.get("direction") == direction]
    if not closed:
        return {"n": 0, "n_tp_sl": 0, "wr": None, "expectancy": None,
                "avg_win": 0, "avg_loss": 0, "time_exits": {"n": 0, "exp": 0}}
    # WR principal = touches TP/SL uniquement ; les sorties à horizon comptent
    # dans l'espérance (pnl réel) mais sont rapportées à part.
    wins = [t for t in closed if t.get("result") == "WIN"]
    losses = [t for t in closed if t.get("result") == "LOSS"]
    time_exits = [t for t in closed if t.get("result") in ("WIN_TIME", "LOSS_TIME")]
    n_tp_sl = len(wins) + len(losses)
    wr = len(wins) / n_tp_sl * 100 if n_tp_sl else None
    avg_win = sum(t.get("pnl_pct", 0) for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t.get("pnl_pct", 0) for t in losses) / len(losses) if losses else 0
    expectancy = sum(t.get("pnl_pct") or 0 for t in closed) / len(closed)
    te_exp = sum(t.get("pnl_pct") or 0 for t in time_exits) / len(time_exits) if time_exits else 0
    return {
        "n": len(closed),
        "n_tp_sl": n_tp_sl,
        "n_wins": len(wins),
        "wr": round(wr, 1) if wr is not None else None,
        "expectancy": round(expectancy, 3),
        "avg_win": round(avg_win, 3),
        "avg_loss": round(avg_loss, 3),
        "time_exits": {"n": len(time_exits), "exp": round(te_exp, 3)},
    }


def _forecast_bias(asset):
    fc = forecast.forecast(asset)
    tf = fc.get("tf", {})
    direction_score = sum(tf.get(k, 0) for k in ("15m", "1h", "4h"))
    if direction_score >= 0.35:
        direction = "LONG"
    elif direction_score <= -0.35:
        direction = "SHORT"
    else:
        direction = "NEUTRAL"
    return fc, direction


def _major_veto(asset, setup, fc, radar_alert):
    reasons = []
    direction = setup.get("direction")
    tf = fc.get("tf", {})
    session = adaptive_edge.current_session(asset)
    if session in ("CLOSED", "WEEKEND", "OVERNIGHT"):
        reasons.append(f"session {session}: spreads élargis, aucun A_SETUP hors session")
    # Fenêtres de volatilité MORTES (vérifié adversarialement 03-07, 16-17 jours,
    # ratio vol/coût <1 chaque jour) : le coût aller-retour dépasse le mouvement
    # typique -> espérance mécaniquement négative, quel que soit le signal.
    h = scanner._paris_hour()
    if asset == "US500" and not (15 <= h < 22):
        reasons.append("US500 hors 15h-22h Paris : vol 5-min < coût aller-retour (fenêtre morte)")
    if h == 23:
        reasons.append("23h-00h Paris : marché quasi figé, spread off-session")
    # ANTI-CHASSE (vérifié 03-07) : prix étiré AU-DESSUS de la Value Area
    # (of_imbalance > +1) -> retours futurs 1h-4h négatifs sur les 2 actifs ;
    # on n'achète pas le haut du profil de volume.
    if direction == "LONG":
        of = fc.get("orderflow") or {}
        vah, val, ref = of.get("vah"), of.get("val"), setup.get("entry")
        if vah and val and ref and vah > val and (ref - val) / (vah - val) > 1.0:
            reasons.append(f"anti-chasse: entrée au-dessus de la Value Area "
                           f"(imb {(ref - val) / (vah - val):.2f} > 1), réversion historique 1h-4h")
    if radar_alert.startswith("🔴"):
        reasons.append("news radar rouge: trop d'incertitude")
    if direction == "LONG" and tf.get("4h", 0) < -0.25:
        reasons.append("4H opposé au long")
    if direction == "SHORT" and tf.get("4h", 0) > 0.25:
        reasons.append("4H opposé au short")
    rr = setup.get("rr", 0)
    if rr > RR_MAX_SANITY:
        reasons.append(f"RR {rr} > {RR_MAX_SANITY}: stop microscopique / TP injoignable (artefact, pas un edge)")
    if setup.get("conf", 0) < CONF_B:
        reasons.append(f"confluence {setup.get('conf')} < {CONF_B}")
    return reasons


def _expectancy_ok(setup):
    """Garde-fou d'espérance pour le grade A — remplace l'ancien RR fixe (>=2).
    Le but c'est le PROFIT, pas un RR : si la stratégie a un historique effectif
    suffisant, on exige son espérance nette historique >= 0 (on refuse de décerner
    un A_SETUP à une stratégie qui perd en moyenne, même avec un bon RR). Sinon
    (cold start, pas d'estimation fiable) on retombe sur un prior RR prudent.
    Dans tous les cas, un plancher de santé minimal RR_A_MIN est requis."""
    rr = setup.get("rr", 0)
    if rr < RR_A_MIN:
        return False
    strat = setup.get("strategy")
    if strat:
        # trader="AI" OBLIGATOIRE (audit 07-02) : sans lui, un futur import USER
        # portant le même label de stratégie contaminerait silencieusement le gate.
        st = _stats_for(strategy=strat, trader="AI")
        if st.get("n", 0) >= MIN_EXP_SAMPLE and st.get("expectancy") is not None:
            return st["expectancy"] >= 0
    return rr >= RR_A_PRIOR


def _grade(setup, vetoes, fc):
    if vetoes:
        return "NO_TRADE"
    conf = setup.get("conf", 0)
    tf = fc.get("tf", {})
    direction = setup.get("direction")
    aligned_tf = (
        direction == "LONG" and tf.get("1h", 0) >= 0 and tf.get("4h", 0) >= -0.15
    ) or (
        direction == "SHORT" and tf.get("1h", 0) <= 0 and tf.get("4h", 0) <= 0.15
    )
    if conf >= CONF_A and aligned_tf and _expectancy_ok(setup):
        return "A_SETUP"
    return "WATCH"


def _adaptive_policy():
    try:
        return adaptive_edge.active_policy()
    except Exception as exc:
        return {
            "mode": "ERROR",
            "label": "ADAPTIVE_EDGE_ERROR",
            "reason": str(exc),
            "filters": {},
        }


def _edge_light(verdict):
    policy = verdict.get("policy") or {}
    summary = policy.get("summary") or {}
    baseline = policy.get("baseline") or {}
    return {
        "accepted": verdict.get("accepted"),
        "action": verdict.get("action"),
        "policy_label": verdict.get("policy_label"),
        "reason": verdict.get("reason"),
        "mode": policy.get("mode"),
        "filters": policy.get("filters"),
        "final_equity": summary.get("final_equity"),
        "baseline_final_equity": baseline.get("final_equity"),
        "improvement_vs_baseline_pct": policy.get("improvement_vs_baseline_pct"),
    }


def _of_compact(fc):
    """Réduit l'order-flow au strict nécessaire pour feature_store (poc/vah/val +
    delta récent). On évite de threader tout le dict orderflow.analyze (signals/
    hvn/lvn) dans la décision : celle-ci est journalisée intégralement à chaque
    cycle (prime_watcher), donc un payload lourd gonflerait le .jsonl pour rien."""
    of = fc.get("orderflow") or {}
    d = of.get("delta") or {}
    if of.get("poc") is None and d.get("recent_delta") is None:
        return None
    return {"poc": of.get("poc"), "vah": of.get("vah"), "val": of.get("val"),
            "recent_delta": d.get("recent_delta")}


def evaluate():
    rad = news_radar.radar()
    alert, msg = news_radar._window_alert(rad)
    scan = scanner.scan()
    edge_policy = _adaptive_policy()
    fc_map = {}
    decisions = []
    setups_by_asset = {s["asset"]: s for s in scan.get("setups", [])}

    for asset in ("GOLD", "US500"):
        fc, fc_dir = _forecast_bias(asset)
        fc_map[asset] = fc
        rg = (scan.get("regimes") or {}).get(asset, {})
        # P1 — jamais de décision tradable sur données mortes : prix indisponible
        # ou >=2 TF intraday en erreur de fetch -> NO_TRADE d'office (source dégradée).
        if fc.get("source_degraded"):
            decisions.append({
                "asset": asset,
                "grade": "NO_TRADE",
                "reason": "source dégradée (prix indisponible ou >=2 TF en erreur) — aucune décision tradable",
                "forecast_direction": fc_dir,
                "forecast_tf": fc.get("tf"),
                "price": fc.get("price"),
                "price_source": fc.get("price_source"),
                "regime": rg.get("regime"),
            })
            continue
        setup = setups_by_asset.get(asset)
        if not setup:
            decisions.append({
                "asset": asset,
                "grade": "NO_TRADE",
                "reason": "aucun setup propre (santé RR / confluence insuffisante)",
                "forecast_direction": fc_dir,
                "forecast_tf": fc.get("tf"),
                "price": fc.get("price"),
                "price_source": fc.get("price_source"),
                "orderflow": _of_compact(fc),
                "regime": rg.get("regime"),
            })
            continue
        vetoes = _major_veto(asset, setup, fc, alert)
        grade = _grade(setup, vetoes, fc)
        decision = {
            "asset": asset,
            "grade": grade,
            "setup": setup,
            "vetoes": vetoes,
            "forecast_direction": fc_dir,
            "forecast_tf": fc.get("tf"),
            "price": fc.get("price"),
            "price_source": fc.get("price_source"),
            "orderflow": _of_compact(fc),
            "regime": setup.get("regime"),
        }
        edge_verdict = adaptive_edge.matches_decision(decision, edge_policy)
        decision["adaptive_edge"] = _edge_light(edge_verdict)
        if grade == "A_SETUP" and not edge_verdict.get("accepted"):
            decision["grade"] = "WATCH"
            decision["reason"] = edge_verdict.get("reason")
        decision["management"] = position_policy.policy_for(decision)
        decisions.append(decision)

    return {
        "ts": datetime.datetime.now().isoformat(),
        "adaptive_edge_policy": {
            "mode": edge_policy.get("mode"),
            "label": edge_policy.get("label"),
            "reason": edge_policy.get("reason"),
            "filters": edge_policy.get("filters"),
            "summary": edge_policy.get("summary"),
            "baseline": edge_policy.get("baseline"),
            "improvement_vs_baseline_pct": edge_policy.get("improvement_vs_baseline_pct"),
        },
        "radar": {
            "alert": alert,
            "message": msg,
            "fear_greed": rad.get("fear_greed"),
            "gold_bias": rad.get("gold_bias"),
            "spx_bias": rad.get("spx_bias"),
            "macro_calendar": rad.get("macro_calendar"),  # sinon macro_cal_mode/surprise_z = NULL au feature_store
        },
        "stats": {
            "ai": _stats_for(trader="AI"),
            "user": _stats_for(trader="USER"),
            "ote": _stats_for(strategy="OTE_RETRACEMENT"),
            "user_scalp_rebond": _stats_for(strategy="SCALP_REBOND", trader="USER"),
        },
        "decisions": decisions,
    }


def should_replace_user_strategy():
    """Verdict statistique conservateur: remplacer seulement si OTE a assez de
    cas EFFECTIFS et que la borne basse de l'IC Wilson de l'IA dépasse le WR user."""
    ai = _stats_for(trader="AI")
    user = _stats_for(trader="USER")
    ote = _stats_for(strategy="OTE_RETRACEMENT")
    scalp = _stats_for(strategy="SCALP_REBOND", trader="USER")
    ai_ci = uncertainty.wilson(ai.get("n_wins", 0), ai.get("n_tp_sl", 0))
    ai_wr_low = ai_ci[0] if ai_ci else 0.0
    replace = (
        ote["n"] >= MIN_OTE_SAMPLE
        and (ote["expectancy"] or -999) > max(user["expectancy"] or -999, scalp["expectancy"] or -999)
        and (ai["expectancy"] or -999) > (user["expectancy"] or -999)
        and ai_wr_low > (user["wr"] or 100)
    )
    return replace, {"ai": ai, "user": user, "ote": ote, "user_scalp_rebond": scalp,
                     "ai_wr_wilson_low": ai_wr_low}


def _fmt_pct(value):
    if value is None:
        return "?"
    return f"{value:+.1f}%"


def _print():
    replace, stats = should_replace_user_strategy()
    data = evaluate()
    print("═" * 72)
    print("  PRIME STRATEGY — protocole de remplacement")
    print("═" * 72)
    print(f"  Verdict remplacement : {'OUI' if replace else 'PAS ENCORE'}")

    def _line(label, st):
        wr_txt = uncertainty.fmt_wr(st["wr"], st.get("n_wins", 0), st.get("n_tp_sl", 0))
        te = st.get("time_exits") or {}
        te_txt = f" · time_exits n={te['n']} exp {te['exp']:+.3f}%" if te.get("n") else ""
        exp = st["expectancy"]
        exp_txt = f"{exp:+.3f}%" if exp is not None else "?"
        print(f"  {label}: {wr_txt} (effectif {st['n']}) exp {exp_txt}{te_txt}")

    _line("IA", stats["ai"])
    _line("USER", stats["user"])
    _line("OTE", stats["ote"])
    _line("Scalp rebond USER", stats["user_scalp_rebond"])
    eff = clusters.effective_trades()
    ai_trades = [t for t in eff if clusters.is_ai(t)]
    ci = uncertainty.bootstrap_exp_by_day(ai_trades)
    if ci:
        print(f"  IA espérance IC95 bootstrap-jours: [{ci[0]:+.3f}%, {ci[1]:+.3f}%]")
    rd = data["radar"]
    ep = data.get("adaptive_edge_policy") or {}
    fg = rd.get("fear_greed") or {}
    print(f"\n  Radar: {rd['alert']} — {rd['message']}")
    print(f"  Fear&Greed {fg.get('score', '?')} ({fg.get('rating', '')}) · news OR {rd['gold_bias']:+d} / S&P {rd['spx_bias']:+d}")
    if ep:
        print(f"  Edge adaptatif: {ep.get('mode')} · {ep.get('label')} — {ep.get('reason')}")
    for d in data["decisions"]:
        print(f"\n  {d['asset']} @ {d.get('price')} · forecast {d.get('forecast_direction')} · régime {d.get('regime')}")
        print(f"  Décision: {d['grade']}")
        if d.get("setup"):
            s = d["setup"]
            print(f"  {s['direction']} conf {s['conf']}/10 · entrée {s['entry']} · stop {s['stop']} · TP {s['tp']} · RR {s['rr']}:1")
            ae = d.get("adaptive_edge") or {}
            if ae:
                print(f"  Edge: {ae.get('action')} · {ae.get('policy_label')} — {ae.get('reason')}")
            m = d.get("management") or {}
            if m:
                print(f"  Gestion: {m['mode']} · entrée valide {m['entry_valid_minutes']}m · review {m['review_after_hours']}h · max {m['max_hold_hours']}h")
                lp = m.get("leverage_profile") or {}
                sz = m.get("sizing") or {}
                if lp:
                    print(
                        f"  Objectif: {m.get('target_policy')} · x{lp.get('leverage')} "
                        f"TP {_fmt_pct(lp.get('tp_x20_pct'))} / SL {_fmt_pct(lp.get('sl_x20_pct'))}"
                    )
                if sz:
                    print(
                        f"  Taille max: {sz.get('max_margin_pct_of_account')}% du capital en marge "
                        f"(risque compte {sz.get('max_account_risk_pct')}%, gain cible estimé {sz.get('expected_account_gain_at_target_pct')}%)"
                    )
                print(f"  Invalidation: {m['manual_invalidations'][0]}; {m['manual_invalidations'][1]}")
        if d.get("vetoes"):
            print("  Veto: " + "; ".join(d["vetoes"]))
        if d.get("reason"):
            print(f"  Raison: {d['reason']}")
    print("═" * 72)


if __name__ == "__main__":
    _print()
