#!/usr/bin/env python3
"""EDGE LAB, recherche d'edge sans sur-optimisation.

Analyse le journal par batchs d'information/stratégie et donne des conclusions
robustes seulement si l'échantillon passe des garde-fous:
  • minimum de trades
  • espérance positive globale
  • train/test chronologique cohérent
  • shrinkage des petits échantillons

Usage:
  python3 edge_lab.py
"""

import collections
import datetime
import json
import math

import clusters

JOURNAL = "/Users/sam/trading/journal.json"
MIN_N = 8
MIN_TEST_N = 3
SHRINK_N = 12


def load_closed():
    # Trades effectifs : clôturés décisifs, doublons IA exclus (clusters.py)
    return clusters.effective_trades()


def stats(trades):
    if not trades:
        return None
    # WR = touches TP/SL uniquement ; l'espérance inclut les sorties à horizon.
    wins = [t for t in trades if t.get("result") == "WIN"]
    losses = [t for t in trades if t.get("result") == "LOSS"]
    time_exits = [t for t in trades if t.get("result") in ("WIN_TIME", "LOSS_TIME")]
    n_tp_sl = len(wins) + len(losses)
    wr = len(wins) / n_tp_sl * 100 if n_tp_sl else None
    avg_win = sum(t.get("pnl_pct", 0) for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t.get("pnl_pct", 0) for t in losses) / len(losses) if losses else 0
    expectancy = sum(t.get("pnl_pct") or 0 for t in trades) / len(trades)
    return {
        "n": len(trades),
        "n_tp_sl": n_tp_sl,
        "wr": round(wr, 1) if wr is not None else None,
        "exp": round(expectancy, 3),
        "avg_win": round(avg_win, 3),
        "avg_loss": round(avg_loss, 3),
        "time_exits": len(time_exits),
    }


def score_candidate(all_stats, train_stats, test_stats):
    if not all_stats or all_stats["n"] < MIN_N:
        return None
    shrink = all_stats["n"] / (all_stats["n"] + SHRINK_N)
    robust_exp = all_stats["exp"] * shrink
    test_ok = bool(test_stats and test_stats["n"] >= MIN_TEST_N and test_stats["exp"] > 0)
    train_ok = bool(train_stats and train_stats["exp"] > 0)
    if test_ok and train_ok and all_stats["exp"] > 0:
        verdict = "KEEP"
    elif all_stats["exp"] > 0 and all_stats["n"] >= MIN_N:
        verdict = "WATCH"
    elif all_stats["exp"] < -0.05 and all_stats["n"] >= MIN_N:
        verdict = "AVOID"
    else:
        verdict = "IGNORE"
    return {
        "verdict": verdict,
        "robust_exp": round(robust_exp, 3),
        "train_ok": train_ok,
        "test_ok": test_ok,
    }


def split_train_test(trades):
    if len(trades) < 2:
        return trades, []
    cut = max(1, int(len(trades) * 0.6))
    return trades[:cut], trades[cut:]


def band_score(t):
    s = t.get("score")
    if s is None:
        return None
    return "8-10" if s >= 8 else "7-8" if s >= 7 else "6-7" if s >= 6 else "<6"


def band_adx(t):
    a = t.get("adx")
    if a is None:
        return None
    return ">35" if a >= 35 else "30-35" if a >= 30 else "20-30" if a >= 20 else "<20"


def macro_regime(t):
    return (t.get("snapshot") or {}).get("macro", {}).get("regime")


def trend_1h(t):
    tech = (t.get("snapshot") or {}).get("technical", {})
    h = tech.get("1h") if tech else None
    if not h:
        return None
    return "uptrend" if h.get("ema_trend") == "↑" else "downtrend"


def trader_type(t):
    return t.get("trader") or ("USER" if t.get("source") == "REAL_TRADE" else "AI")


def concepts(trade):
    return trade.get("smc_concepts") or []


DIMENSIONS = {
    "trader": trader_type,
    "asset": lambda t: t.get("asset"),
    "direction": lambda t: t.get("direction"),
    "strategy": lambda t: t.get("strategy"),
    "session": lambda t: t.get("session"),
    "score_band": band_score,
    "adx_band": band_adx,
    "macro_regime": macro_regime,
    "trend_1h": trend_1h,
}


def group_candidates(trades):
    candidates = []
    for dim, keyfn in DIMENSIONS.items():
        groups = collections.defaultdict(list)
        for t in trades:
            key = keyfn(t)
            if key is not None:
                groups[key].append(t)
        for key, group in groups.items():
            train, test = split_train_test(group)
            st_all = stats(group)
            st_train = stats(train)
            st_test = stats(test)
            sc = score_candidate(st_all, st_train, st_test)
            if sc:
                candidates.append({
                    "dim": dim,
                    "key": key,
                    "all": st_all,
                    "train": st_train,
                    "test": st_test,
                    **sc,
                })

    smc_groups = collections.defaultdict(list)
    for t in trades:
        for c in concepts(t):
            smc_groups[c].append(t)
    for key, group in smc_groups.items():
        train, test = split_train_test(group)
        st_all = stats(group)
        st_train = stats(train)
        st_test = stats(test)
        sc = score_candidate(st_all, st_train, st_test)
        if sc:
            candidates.append({
                "dim": "smc_concept",
                "key": key,
                "all": st_all,
                "train": st_train,
                "test": st_test,
                **sc,
            })
    return candidates


def main():
    trades = load_closed()
    candidates = group_candidates(trades)
    rank = {"KEEP": 0, "WATCH": 1, "AVOID": 2, "IGNORE": 3}
    candidates.sort(key=lambda c: (rank.get(c["verdict"], 9), -c["robust_exp"], -c["all"]["n"]))

    print("═" * 76)
    print("  EDGE LAB, robustesse des edges du journal")
    print("═" * 76)
    print(f"  Trades clôturés analysés: {len(trades)} | min_n={MIN_N} | split=60/40 | shrink_n={SHRINK_N}")
    for verdict in ("KEEP", "WATCH", "AVOID"):
        rows = [c for c in candidates if c["verdict"] == verdict]
        if not rows:
            continue
        print(f"\n  ── {verdict} ──")
        for c in rows[:12]:
            a = c["all"]
            tr = c["train"] or {"n": 0, "exp": 0}
            te = c["test"] or {"n": 0, "exp": 0}
            print(
                f"   {c['dim']}={c['key']} | n={a['n']} WR={a['wr']}% exp={a['exp']:+.3f}% "
                f"robust={c['robust_exp']:+.3f}% | train {tr['n']}:{tr['exp']:+.3f}% "
                f"test {te['n']}:{te['exp']:+.3f}%"
            )
    print("\n  Règle: KEEP = exploitable, WATCH = prometteur mais pas encore robuste, AVOID = filtre négatif.")
    print("═" * 76)


if __name__ == "__main__":
    main()
