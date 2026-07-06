#!/usr/bin/env python3
"""RESIM REPORT, le verdict honnête sur le protocole Prime.

Recalcule tout le journal IA avec déduplication + coûts + WIN_TIME séparé,
et imprime le tableau avant/après :

  AVANT  = ce que le journal affichait (signaux bruts, sorties au prix exact,
           WIN_TIME compté comme win), la base du "remplace ta stratégie".
  APRÈS  = trades effectifs (1 position = 1 trade), sorties nettes de spread/
           slippage/swap, WR = touches TP/SL uniquement, IC affichés.

Aucune conclusion de remplacement de stratégie avant un mois de forward-test
avec CETTE mesure.
"""

import clusters
import costs
import uncertainty

START_EQUITY = 1000.0
LEVERAGE = 20
ACCOUNT_RISK_CAP_PCT = 4.0

DECISIVE = ("WIN", "WIN_TIME", "LOSS", "LOSS_TIME")


def _ret_pct(entry, exit_price, direction):
    sign = 1 if direction == "LONG" else -1
    return sign * (exit_price - entry) / entry * 100


def outcome(t, with_costs):
    """Résultat re-simulé depuis hi_since/lo_since (SL d'abord si ambigu).

    Retourne (kind, pnl_pct) avec kind ∈ TP/SL/TIME/UNKNOWN.
    """
    entry, stop, tp = t.get("entry"), t.get("stop"), t.get("tp1")
    hi, lo = t.get("hi_since"), t.get("lo_since")
    direction = t.get("direction")
    if None in (entry, stop, tp, hi, lo) or direction not in ("LONG", "SHORT"):
        # Pas de données d'extrêmes : on garde le résultat stocké tel quel
        return "UNKNOWN", t.get("pnl_pct") or 0.0

    sign = 1 if direction == "LONG" else -1
    sl_hit = lo <= stop if sign > 0 else hi >= stop
    tp_hit = hi >= tp if sign > 0 else lo <= tp
    swap = costs.swap_pct(t.get("asset"), costs.nights_held(t.get("ts", ""), t.get("closed_ts", ""))) if with_costs else 0.0

    if sl_hit:
        exit_price = costs.adjust_exit(t["asset"], stop, direction, t.get("session"), "sl") if with_costs else stop
        return "SL", _ret_pct(entry, exit_price, direction) - swap
    if tp_hit:
        exit_price = costs.adjust_exit(t["asset"], tp, direction, t.get("session"), "tp") if with_costs else tp
        return "TP", _ret_pct(entry, exit_price, direction) - swap
    # Sortie à horizon : pnl stocké, dégradé du spread de sortie + swap
    pnl = t.get("pnl_pct") or 0.0
    if with_costs and not t.get("costs_applied"):
        spread_pct = costs.spread_points(t["asset"], t.get("session"), entry) / entry * 100
        pnl -= spread_pct + swap
    return "TIME", pnl


def equity_x20(trades, with_costs):
    """Capital final x20 avec risque compte cappé à 4% par trade (TP/SL seuls)."""
    equity = START_EQUITY
    for t in trades:
        kind, pnl = outcome(t, with_costs)
        if kind not in ("TP", "SL"):
            continue
        sl_pct = abs(_ret_pct(t["entry"], t["stop"], t["direction"]))
        sl_x20 = sl_pct * LEVERAGE
        if sl_x20 <= 0:
            continue
        margin_fraction = min(1.0, ACCOUNT_RISK_CAP_PCT / sl_x20)
        equity *= 1 + pnl * LEVERAGE * margin_fraction / 100
    return round(equity, 2)


def block(trades, with_costs, dedup_label):
    tp = sl = 0
    pnls, time_pnls = [], []
    for t in trades:
        kind, pnl = outcome(t, with_costs)
        if kind == "TP":
            tp += 1
            pnls.append(pnl)
        elif kind == "SL":
            sl += 1
            pnls.append(pnl)
        elif kind == "TIME":
            time_pnls.append(pnl)
            pnls.append(pnl)
        else:
            pnls.append(pnl)
    n_tp_sl = tp + sl
    wr = tp / n_tp_sl * 100 if n_tp_sl else None
    exp = sum(pnls) / len(pnls) if pnls else None
    return {
        "label": dedup_label,
        "n": len(trades),
        "n_tp_sl": n_tp_sl,
        "tp": tp,
        "sl": sl,
        "time": len(time_pnls),
        "time_exp": round(sum(time_pnls) / len(time_pnls), 3) if time_pnls else 0.0,
        "wr": round(wr, 1) if wr is not None else None,
        "wilson": uncertainty.wilson(tp, n_tp_sl) if n_tp_sl else None,
        "exp": round(exp, 3) if exp is not None else None,
        "boot": uncertainty.bootstrap_exp_by_day(
            [dict(t, pnl_pct=outcome(t, with_costs)[1]) for t in trades]
        ),
        "equity": equity_x20(trades, with_costs),
    }


def legacy_wr(trades):
    """L'ancien calcul : WIN_TIME compté comme win, tous signaux confondus."""
    wins = [t for t in trades if str(t.get("result", "")).startswith("WIN")]
    return round(len(wins) / len(trades) * 100, 1) if trades else None


def main():
    j = clusters.load_journal_raw()
    raw_ai = [
        t for t in j.get("signals", [])
        if clusters.is_ai(t) and t.get("result") in DECISIVE
    ]
    raw_ai.sort(key=clusters.parse_ts)
    eff_ai = [t for t in clusters.effective_trades(j) if clusters.is_ai(t)]

    before = block(raw_ai, with_costs=False, dedup_label="brut (signaux, sans coûts)")
    after = block(eff_ai, with_costs=True, dedup_label="effectif (positions, net de coûts)")

    user = [t for t in clusters.effective_trades(j) if not clusters.is_ai(t)]
    u_wins = sum(t.get("result") == "WIN" for t in user)
    u_losses = sum(t.get("result") == "LOSS" for t in user)
    u_wr = round(u_wins / (u_wins + u_losses) * 100, 1) if u_wins + u_losses else None
    u_exp = round(sum(t.get("pnl_pct") or 0 for t in user) / len(user), 3) if user else None

    print("═" * 74)
    print("  RESIM REPORT, protocole Prime, mesure corrigée")
    print("═" * 74)
    print(f"  Référence USER (fills réels Revolut): WR {u_wr}% "
          f"[IC95 {uncertainty.wilson(u_wins, u_wins + u_losses)}] n={len(user)} exp {u_exp:+.3f}%")
    print(f"  Ancien affichage IA (WIN_TIME=win, doublons inclus): "
          f"WR {legacy_wr(raw_ai)}% n={len(raw_ai)}")
    print()
    hdr = f"  {'':34} {'AVANT':>16} {'APRÈS':>20}"
    print(hdr)
    rows = [
        ("n trades", before["n"], after["n"]),
        ("n décisifs TP/SL", before["n_tp_sl"], after["n_tp_sl"]),
        ("TP / SL", f"{before['tp']} / {before['sl']}", f"{after['tp']} / {after['sl']}"),
        ("sorties horizon (hors WR)", f"{before['time']} ({before['time_exp']:+.3f}%)",
         f"{after['time']} ({after['time_exp']:+.3f}%)"),
        ("WR TP/SL", f"{before['wr']}%", f"{after['wr']}%"),
        ("IC Wilson 95%", f"{before['wilson']}", f"{after['wilson']}"),
        ("espérance %/trade", f"{before['exp']:+.3f}", f"{after['exp']:+.3f}"),
        ("IC bootstrap-jours", f"{before['boot']}", f"{after['boot']}"),
        ("equity x20 simulée (1000€)", f"{before['equity']}€", f"{after['equity']}€"),
    ]
    for name, b, a in rows:
        print(f"  {name:34} {str(b):>16} {str(a):>20}")
    print()
    n_eff = after["n_tp_sl"]
    if n_eff < uncertainty.MIN_EFFECTIVE_N:
        print(f"  ⚠ ÉCHANTILLON INSUFFISANT : {n_eff} trades décisifs effectifs "
              f"(minimum {uncertainty.MIN_EFFECTIVE_N}).")
    lo_ok = after["boot"] and after["boot"][0] > 0
    print("  Verdict : " + (
        "edge net de coûts encore non prouvé, l'IC de l'espérance contient 0."
        if not lo_ok else
        "espérance nette positive sur l'IC, à confirmer par forward-test."
    ))
    print("  Aucune décision de remplacement avant 1 mois de forward-test avec cette mesure.")
    print("═" * 74)


if __name__ == "__main__":
    main()
