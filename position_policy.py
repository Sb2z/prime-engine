#!/usr/bin/env python3
"""POSITION POLICY — durée et invalidation des setups Prime.

Objectif : décider si un setup doit être tenu jusqu'au TP/SL ou géré avec une
invalidation manuelle. La règle est dérivée du journal, puis appliquée aux
alertes Prime.

Limite actuelle : le journal ne stocke pas l'heure exacte de touche TP/SL, donc
on raisonne sur résultat, MFE/MAE et clôture à horizon 8h.
"""

import collections

import clusters
import costs
import journal


DEFAULT_MAX_HOLD_HOURS = 8
REVIEW_AFTER_HOURS = 4
ENTRY_VALID_MINUTES = 45
LEVERAGE = 20
TARGET_EVIDENCE_MIN = 6

MAX_ACCOUNT_RISK = {
    "HOLD_TP1_SL": 4.0,
    "HOLD_TP1_SL_WITH_CONTEXT_VETO": 3.0,
    "MANAGED": 2.0,
}


def _closed_ai():
    rows = []
    # Doublons IA exclus : une position virtuelle = un trade (clusters.py)
    for t in clusters.non_duplicates():
        if not clusters.is_ai(t) or t.get("status") != "CLOSED":
            continue
        if t.get("result") not in ("WIN", "WIN_TIME", "LOSS", "LOSS_TIME", "FLAT"):
            continue
        rows.append(t)
    return rows


def _ai_target_rows():
    rows = []
    for t in clusters.non_duplicates():
        if not clusters.is_ai(t):
            continue
        if t.get("direction") not in ("LONG", "SHORT"):
            continue
        if not all(t.get(k) is not None for k in ("entry", "stop", "hi_since", "lo_since")):
            continue
        rows.append(t)
    return rows


def _stats(rows):
    decisive = [t for t in rows if t.get("result") in ("WIN", "WIN_TIME", "LOSS", "LOSS_TIME")]
    # WR = touches TP/SL uniquement (les *_TIME restent comptés dans l'espérance)
    wins = [t for t in decisive if t.get("result") == "WIN"]
    losses = [t for t in decisive if t.get("result") == "LOSS"]
    return {
        "n": len(rows),
        "decisive": len(decisive),
        "tp": sum(t.get("result") == "WIN" for t in rows),
        "win_time": sum(t.get("result") == "WIN_TIME" for t in rows),
        "sl": sum(t.get("result") == "LOSS" for t in rows),
        "loss_time": sum(t.get("result") == "LOSS_TIME" for t in rows),
        "flat": sum(t.get("result") == "FLAT" for t in rows),
        "wr": round(len(wins) / (len(wins) + len(losses)) * 100, 1) if (wins or losses) else None,
        "expectancy": round(sum(t.get("pnl_pct", 0) for t in decisive) / len(decisive), 3) if decisive else 0,
        "avg_mfe": round(sum(t.get("mfe_pct", 0) for t in rows) / len(rows), 3) if rows else 0,
        "avg_mae": round(sum(t.get("mae_pct", 0) for t in rows) / len(rows), 3) if rows else 0,
    }


def _trade_return_pct(entry, exit_price, direction):
    sign = 1 if direction == "LONG" else -1
    return sign * (exit_price - entry) / entry * 100


def _target_outcome(t, target):
    if t.get("status") == "OPEN":
        return "OPEN", 0.0
    entry = t.get("entry")
    stop = t.get("stop")
    tp = t.get(target)
    hi = t.get("hi_since")
    lo = t.get("lo_since")
    direction = t.get("direction")
    if None in (entry, stop, tp, hi, lo) or direction not in ("LONG", "SHORT"):
        return "NO_DATA", 0.0

    sign = 1 if direction == "LONG" else -1
    sl_hit = lo <= stop if sign > 0 else hi >= stop
    tp_hit = hi >= tp if sign > 0 else lo <= tp

    # Conservateur: si les deux niveaux apparaissent touchés dans la fenêtre, le SL gagne.
    # Coûts inclus : slippage sur stop, spread sur TP, swap si nuits connues.
    swap = costs.swap_pct(t.get("asset"), costs.nights_held(t.get("ts", ""), t.get("closed_ts", "")))
    if sl_hit:
        exit_price = costs.adjust_exit(t.get("asset"), stop, direction, t.get("session"), "sl")
        return "SL", _trade_return_pct(entry, exit_price, direction) - swap
    if tp_hit:
        exit_price = costs.adjust_exit(t.get("asset"), tp, direction, t.get("session"), "tp")
        return "TP", _trade_return_pct(entry, exit_price, direction) - swap
    return "NO_HIT", 0.0


def _target_stats(rows, target):
    known = []
    for t in rows:
        result, ret_pct = _target_outcome(t, target)
        if result in ("NO_DATA", "OPEN"):
            continue
        known.append((result, ret_pct))
    n = len(known)
    tp = sum(r == "TP" for r, _ in known)
    sl = sum(r == "SL" for r, _ in known)
    no_hit = sum(r == "NO_HIT" for r, _ in known)
    expectancy = sum(ret for _, ret in known) / n if n else 0
    return {
        "n": n,
        "tp": tp,
        "sl": sl,
        "no_hit": no_hit,
        "wr": round(tp / (tp + sl) * 100, 1) if tp + sl else None,
        "expectancy": round(expectancy, 3),
        "expectancy_x20": round(expectancy * LEVERAGE, 2),
    }


def target_selection():
    """Choix TP1/TP2 piloté par le journal, pas par dogme."""
    rows = _ai_target_rows()
    tp1 = _target_stats(rows, "tp1")
    tp2 = _target_stats(rows, "tp2")

    enough = tp1["n"] >= TARGET_EVIDENCE_MIN and tp2["n"] >= TARGET_EVIDENCE_MIN
    tp2_margin = max(tp1["expectancy"] * 1.15, tp1["expectancy"] + 0.05)
    if enough and tp2["expectancy"] > tp2_margin:
        preferred = "TP2"
        reason = "TP2 bat TP1 avec marge suffisante sur l'echantillon courant."
    else:
        preferred = "TP1"
        reason = "TP1 garde la meilleure esperance ajustee; TP2 reste surveille."

    return {
        "preferred": preferred,
        "reason": reason,
        "tp1": tp1,
        "tp2": tp2,
        "min_n": TARGET_EVIDENCE_MIN,
    }


def leverage_profile(setup):
    direction = setup.get("direction")
    entry = setup.get("entry")
    stop = setup.get("stop")
    tp = setup.get("tp") or setup.get("tp1")
    if direction not in ("LONG", "SHORT") or not all(isinstance(v, (int, float)) for v in (entry, stop, tp)):
        return {}

    tp_pct = _trade_return_pct(entry, tp, direction)
    sl_pct = _trade_return_pct(entry, stop, direction)
    rr = abs(tp_pct / sl_pct) if sl_pct else None
    return {
        "leverage": LEVERAGE,
        "target_price": tp,
        "tp_pct": round(tp_pct, 3),
        "sl_pct": round(sl_pct, 3),
        "tp_x20_pct": round(tp_pct * LEVERAGE, 2),
        "sl_x20_pct": round(sl_pct * LEVERAGE, 2),
        "rr": round(rr, 2) if rr is not None else None,
    }


MIN_EFFECTIVE_N_FOR_KELLY = 15
MIN_RISK_PCT = 1.0  # risque compte minimum tant que l'échantillon est insuffisant


def _sizing(profile, mode, ai_stats=None):
    """Sizing quart-de-Kelly borné par le cap de risque du mode.

    f = 0.25 x (WR - (1-WR)/RR) sur le WR effectif TP/SL. Tant que
    l'échantillon effectif est < 15, on force le risque minimum (1% compte) :
    pas de décision de taille sur des stats non prouvées.
    """
    sl_x20 = abs(profile.get("sl_x20_pct") or 0)
    tp_x20 = profile.get("tp_x20_pct")
    risk_cap = MAX_ACCOUNT_RISK.get(mode, 2.0)
    if sl_x20 <= 0:
        return {
            "max_account_risk_pct": risk_cap,
            "max_margin_pct_of_account": None,
            "max_notional_pct_of_account": None,
            "expected_account_gain_at_target_pct": None,
        }

    ai_stats = ai_stats or {}
    n_eff = (ai_stats.get("tp") or 0) + (ai_stats.get("sl") or 0)
    wr = ai_stats.get("wr")
    rr = profile.get("rr")
    if n_eff < MIN_EFFECTIVE_N_FOR_KELLY or wr is None or not rr:
        risk_pct = min(MIN_RISK_PCT, risk_cap)
        basis = f"MIN_RISK (échantillon effectif {n_eff} < {MIN_EFFECTIVE_N_FOR_KELLY})"
    else:
        p = wr / 100
        f_kelly = 0.25 * (p - (1 - p) / rr)
        risk_pct = max(0.0, min(risk_cap, f_kelly * 100))
        basis = f"QUARTER_KELLY (WR {wr}% RR {rr} n_eff {n_eff})"

    margin_fraction = min(100.0, risk_pct / sl_x20 * 100)
    return {
        "max_account_risk_pct": round(risk_pct, 2),
        "risk_cap_pct": risk_cap,
        "sizing_basis": basis,
        "max_margin_pct_of_account": round(margin_fraction, 1),
        "max_notional_pct_of_account": round(margin_fraction * LEVERAGE, 1),
        "expected_account_gain_at_target_pct": round((tp_x20 or 0) * margin_fraction / 100, 2),
        "full_margin_sl_pct": round(-sl_x20, 2),
        "full_margin_tp_pct": round(tp_x20 or 0, 2),
    }


def evidence():
    rows = _closed_ai()
    by_strategy = collections.defaultdict(list)
    by_direction = collections.defaultdict(list)
    for t in rows:
        by_strategy[t.get("strategy") or "None"].append(t)
        by_direction[t.get("direction")].append(t)
    return {
        "all_ai": _stats(rows),
        "by_strategy": {k: _stats(v) for k, v in by_strategy.items()},
        "by_direction": {k: _stats(v) for k, v in by_direction.items()},
    }


def policy_for(decision):
    """Retourne une consigne de gestion de position pour une décision Prime."""
    setup = decision.get("setup") or {}
    strategy = setup.get("strategy")
    direction = setup.get("direction")
    regime = setup.get("regime") or decision.get("regime") or ""
    conf = setup.get("conf", 0) or 0

    ev = evidence()
    strategy_stats = ev["by_strategy"].get(strategy or "None", {})
    direction_stats = ev["by_direction"].get(direction, {})

    is_prime_continuation = (
        strategy == "OTE_RETRACEMENT"
        or conf >= 8
        or "TENDANCE" in regime
    )

    if strategy == "OTE_RETRACEMENT":
        mode = "HOLD_TP1_SL"
        thesis = "OTE a le meilleur historique: tenir jusqu'au TP1/SL, pas de sortie émotionnelle."
    elif is_prime_continuation and direction == "SHORT":
        mode = "HOLD_TP1_SL_WITH_CONTEXT_VETO"
        thesis = "Short/continuation robuste, mais hors OTE on garde un veto contexte."
    else:
        mode = "MANAGED"
        thesis = "Historique moins robuste: gestion active et durée plus courte."

    max_hold = DEFAULT_MAX_HOLD_HOURS
    review_after = REVIEW_AFTER_HOURS
    if mode == "MANAGED":
        max_hold = 4
        review_after = 2

    target = target_selection()
    if target["preferred"] == "TP2" and mode != "MANAGED":
        target_policy = "TP2_DYNAMIC_IF_CONTEXT_CONFIRMS"
        default_exit = "TP2 ou SL, avec review obligatoire"
    elif mode == "MANAGED":
        target_policy = "TP1_MANAGED_FAST"
        default_exit = "TP1 ou invalidation active"
    else:
        target_policy = "TP1_FULL_EXIT"
        default_exit = "TP1 ou SL"

    profile = leverage_profile(setup)
    sizing = _sizing(profile, mode, ev["all_ai"]) if profile else {}

    manual_invalidations = [
        "Prime repasse NO_TRADE et le forecast 15m+1h est opposé au trade",
        "News Radar devient rouge / news contradictoire majeure",
        "Clôture 15m nette au-delà de la zone d'invalidation structurelle",
        f"Après {review_after}h: fermer ou réduire si MFE faible et forecast non aligné",
    ]

    return {
        "mode": mode,
        "entry_valid_minutes": ENTRY_VALID_MINUTES,
        "review_after_hours": review_after,
        "max_hold_hours": max_hold,
        "default_exit": default_exit,
        "target_policy": target_policy,
        "profit_objective": {
            "mode": "MAX_EXPECTED_X20_WITH_CAPPED_ACCOUNT_RISK",
            "preferred_target": target["preferred"],
            "reason": target["reason"],
            "target_evidence": {"tp1": target["tp1"], "tp2": target["tp2"]},
        },
        "leverage_profile": profile,
        "sizing": sizing,
        "manual_invalidations": manual_invalidations,
        "thesis": thesis,
        "evidence": {
            "strategy": strategy_stats,
            "direction": direction_stats,
        },
    }


def main():
    ev = evidence()
    target = target_selection()
    print("═" * 72)
    print("  POSITION POLICY — analyse durée / invalidation")
    print("═" * 72)
    print(f"  IA globale: {ev['all_ai']}")
    print(f"  Cible actuelle: {target['preferred']} — {target['reason']}")
    print(f"   TP1: {target['tp1']}")
    print(f"   TP2: {target['tp2']}")
    print("\n  Par stratégie")
    for k, v in sorted(ev["by_strategy"].items(), key=lambda x: x[1]["expectancy"], reverse=True):
        print(f"   {k}: {v}")
    print("\n  Règle actuelle:")
    print("   OTE/Prime robuste: cible dynamique actuelle, review 4h, max 8h.")
    print("   Non-OTE/moins robuste: gestion active, review 2h, max 4h.")
    print("   Levier x20: taille reduite pour capper le risque compte par setup.")
    print("═" * 72)


if __name__ == "__main__":
    main()
