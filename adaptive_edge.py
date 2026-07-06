#!/usr/bin/env python3
"""Adaptive Edge, auto-evaluation x20 des regles Prime.

Le module compare le baseline a des politiques plus restrictives:
actif, sens, strategie, session et plages horaires. Une restriction ne devient
active que si elle augmente le capital final en x20, avec assez de trades et un
split chronologique train/test positif.
"""

import datetime as dt
import json
import tz

import clusters
import costs
import position_policy


JOURNAL = "/Users/sam/trading/journal.json"
STATE_FILE = "/Users/sam/trading/adaptive_edge_state.json"

START_EQUITY = 1000.0
LEVERAGE = 20
ACCOUNT_RISK_CAP_PCT = 4.0
MIN_ACTIVE_N = 15          # trades effectifs (post-dédup)
MIN_TEST_N = 6
MIN_DECISIVE_N = 3
MIN_IMPROVEMENT_PCT = 3.0  # plancher; relevé selon le nb de candidats testés
MAX_DD_WORSE_TOLERANCE = 2.0
WF_WINDOWS = 3             # walk-forward roulant, test positif sur >= 2/3
CANDIDATE_BUDGET = 25      # base de la correction de comparaisons multiples


def _parse_ts(t):
    try:
        return dt.datetime.fromisoformat(t.get("ts", ""))
    except Exception:
        return dt.datetime.min.replace(tzinfo=dt.timezone.utc)


def _paris_hour(t):
    paris = t.get("paris") or ""
    if len(paris) >= 13:
        try:
            return int(paris[11:13])
        except Exception:
            pass
    ts = _parse_ts(t)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=dt.timezone.utc)
    return tz.to_paris(ts).hour


def _is_ai(t):
    trader = t.get("trader") or ("USER" if t.get("source") == "REAL_TRADE" else "AI")
    return trader == "AI"


def load_trades():
    rows = []
    # Doublons IA exclus : une position virtuelle = un trade (clusters.py)
    for t in clusters.non_duplicates():
        if not _is_ai(t) or t.get("status") == "OPEN":
            continue
        if t.get("direction") not in ("LONG", "SHORT"):
            continue
        if not all(t.get(k) is not None for k in ("entry", "stop", "hi_since", "lo_since")):
            continue
        rows.append(t)
    rows.sort(key=_parse_ts)
    return rows


def _trade_return_pct(entry, exit_price, direction):
    sign = 1 if direction == "LONG" else -1
    return sign * (exit_price - entry) / entry * 100


def _target_outcome(t, target):
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
    # Coûts inclus : slippage sur stop, spread sur TP, swap si nuits connues
    swap = costs.swap_pct(t.get("asset"), costs.nights_held(t.get("ts", ""), t.get("closed_ts", "")))
    if sl_hit:
        exit_price = costs.adjust_exit(t.get("asset"), stop, direction, t.get("session"), "sl")
        return "SL", _trade_return_pct(entry, exit_price, direction) - swap
    if tp_hit:
        exit_price = costs.adjust_exit(t.get("asset"), tp, direction, t.get("session"), "tp")
        return "TP", _trade_return_pct(entry, exit_price, direction) - swap
    return "NO_HIT", 0.0


def _account_return_pct(t, target):
    result, raw_ret_pct = _target_outcome(t, target)
    if result not in ("TP", "SL"):
        return result, 0.0

    sl_pct = _trade_return_pct(t["entry"], t["stop"], t["direction"])
    sl_x20 = abs(sl_pct * LEVERAGE)
    if sl_x20 <= 0:
        return result, 0.0
    margin_fraction = min(1.0, ACCOUNT_RISK_CAP_PCT / sl_x20)
    return result, raw_ret_pct * LEVERAGE * margin_fraction


def simulate(trades, target):
    equity = START_EQUITY
    peak = equity
    max_dd = 0.0
    counts = {"TP": 0, "SL": 0, "NO_HIT": 0, "NO_DATA": 0}
    returns = []

    for t in trades:
        result, account_ret_pct = _account_return_pct(t, target)
        counts[result] = counts.get(result, 0) + 1
        returns.append(account_ret_pct)
        equity *= 1 + account_ret_pct / 100
        peak = max(peak, equity)
        if peak > 0:
            max_dd = min(max_dd, (equity - peak) / peak * 100)

    decisive = counts.get("TP", 0) + counts.get("SL", 0)
    win_rate = counts.get("TP", 0) / decisive * 100 if decisive else None
    expectancy = sum(returns) / len(returns) if returns else 0.0
    return {
        "n": len(trades),
        "decisive": decisive,
        "tp": counts.get("TP", 0),
        "sl": counts.get("SL", 0),
        "no_hit": counts.get("NO_HIT", 0),
        "final_equity": round(equity, 2),
        "profit_pct": round((equity / START_EQUITY - 1) * 100, 2),
        "max_dd_pct": round(max_dd, 2),
        "win_rate": round(win_rate, 1) if win_rate is not None else None,
        "expectancy_account_pct": round(expectancy, 3),
        "target": target.upper(),
    }


def _walk_forward(trades, target, n_windows=WF_WINDOWS):
    """Fenêtres roulantes chronologiques : train s'étend, test avance.

    Avec n_windows=3 : train [0:q1] test (q1:q2], train [0:q2] test (q2:q3],
    train [0:q3] test (q3:fin]. Retourne [] si trop peu de trades.
    """
    n = len(trades)
    if n < n_windows + 1:
        return []
    bounds = [max(1, int(n * (i + 1) / (n_windows + 1))) for i in range(n_windows + 1)]
    bounds[-1] = n
    windows = []
    for i in range(n_windows):
        train = trades[:bounds[i]]
        test = trades[bounds[i]:bounds[i + 1]]
        if not test:
            continue
        windows.append({"train": simulate(train, target), "test": simulate(test, target)})
    return windows


def _score_band(value):
    if value is None:
        return None
    return "8-10" if value >= 8 else "7-8" if value >= 7 else "6-7" if value >= 6 else "<6"


def _hour_in_window(hour, start, end):
    if start < end:
        return start <= hour < end
    return hour >= start or hour < end


def _candidate(label, filters, trades):
    return {"label": label, "filters": filters, "trades": trades}


def build_candidates(trades):
    candidates = [_candidate("BASELINE_ALL", {}, trades)]

    def add_group(label, filters, pred):
        group = [t for t in trades if pred(t)]
        if group:
            candidates.append(_candidate(label, filters, group))

    for asset in sorted({t.get("asset") for t in trades if t.get("asset")}):
        add_group(f"asset={asset}", {"asset": asset}, lambda t, asset=asset: t.get("asset") == asset)

    for direction in ("LONG", "SHORT"):
        add_group(
            f"direction={direction}",
            {"direction": direction},
            lambda t, direction=direction: t.get("direction") == direction,
        )

    for asset in sorted({t.get("asset") for t in trades if t.get("asset")}):
        for direction in ("LONG", "SHORT"):
            add_group(
                f"asset={asset}+direction={direction}",
                {"asset": asset, "direction": direction},
                lambda t, asset=asset, direction=direction: t.get("asset") == asset and t.get("direction") == direction,
            )

    for strategy in sorted({t.get("strategy") or "None" for t in trades}):
        add_group(
            f"strategy={strategy}",
            {"strategy": strategy},
            lambda t, strategy=strategy: (t.get("strategy") or "None") == strategy,
        )

    for session in sorted({t.get("session") for t in trades if t.get("session")}):
        add_group(
            f"session={session}",
            {"session": session},
            lambda t, session=session: t.get("session") == session,
        )

    for band in ("8-10", "7-8", "6-7", "<6"):
        add_group(
            f"score_band={band}",
            {"score_band": band},
            lambda t, band=band: _score_band(t.get("score")) == band,
        )

    # Pas de fenêtres horaires glissantes (72 x 3 largeurs = data mining garanti
    # sur ~15 trades autocorrélés). Seules les sessions NOMMÉES sont candidates.
    return candidates


def _enrich_candidate(candidate, target, baseline, required_improvement_pct):
    trades = candidate["trades"]
    summary = simulate(trades, target)
    windows = _walk_forward(trades, target)
    improvement = (summary["final_equity"] / baseline["final_equity"] - 1) * 100 if baseline["final_equity"] else 0

    test_positive = sum(1 for w in windows if w["test"]["expectancy_account_pct"] > 0)
    test_n_total = sum(w["test"]["n"] for w in windows)

    active = (
        candidate["label"] != "BASELINE_ALL"
        and summary["n"] >= MIN_ACTIVE_N
        and summary["decisive"] >= MIN_DECISIVE_N
        and test_n_total >= MIN_TEST_N
        and len(windows) == WF_WINDOWS
        and test_positive >= 2  # espérance test > 0 sur au moins 2 fenêtres / 3
        and improvement >= required_improvement_pct
        and abs(summary["max_dd_pct"]) <= abs(baseline["max_dd_pct"]) + MAX_DD_WORSE_TOLERANCE
    )

    return {
        "label": candidate["label"],
        "filters": candidate["filters"],
        "summary": summary,
        "walk_forward": [
            {"train_n": w["train"]["n"], "test_n": w["test"]["n"],
             "test_exp": w["test"]["expectancy_account_pct"]}
            for w in windows
        ],
        "wf_test_positive": test_positive,
        "improvement_vs_baseline_pct": round(improvement, 2),
        "active_eligible": active,
    }


def evaluate(target=None):
    if target is None:
        target = position_policy.target_selection()["preferred"].lower()
    trades = load_trades()
    baseline = simulate(trades, target)
    candidates = build_candidates(trades)
    # Correction de comparaisons multiples : plus on teste de candidats,
    # plus l'amélioration exigée monte.
    n_tested = max(0, len(candidates) - 1)
    required_improvement = max(
        MIN_IMPROVEMENT_PCT,
        MIN_IMPROVEMENT_PCT * (n_tested / CANDIDATE_BUDGET) ** 0.5,
    )
    enriched = [_enrich_candidate(c, target, baseline, required_improvement) for c in candidates]
    enriched.sort(
        key=lambda c: (
            not c["active_eligible"],
            -c["summary"]["final_equity"],
            abs(c["summary"]["max_dd_pct"]),
            -c["summary"]["n"],
        )
    )
    active = next((c for c in enriched if c["active_eligible"]), None)
    if active is None:
        active = next(c for c in enriched if c["label"] == "BASELINE_ALL")
    return {
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
        "target": target.upper(),
        "start_equity": START_EQUITY,
        "leverage": LEVERAGE,
        "account_risk_cap_pct": ACCOUNT_RISK_CAP_PCT,
        "baseline": baseline,
        "active": active,
        "top": enriched[:15],
        "rules": {
            "min_active_n": MIN_ACTIVE_N,
            "min_test_n": MIN_TEST_N,
            "min_decisive_n": MIN_DECISIVE_N,
            "min_improvement_pct": MIN_IMPROVEMENT_PCT,
            "required_improvement_pct": round(required_improvement, 2),
            "candidates_tested": n_tested,
            "walk_forward_windows": WF_WINDOWS,
        },
    }


def active_policy():
    report = evaluate()
    active = report["active"]
    baseline = report["baseline"]
    mode = "ACTIVE_FILTER" if active["label"] != "BASELINE_ALL" else "BASELINE"
    if mode == "ACTIVE_FILTER":
        reason = (
            f"{active['label']} bat le baseline: "
            f"{active['summary']['final_equity']}€ vs {baseline['final_equity']}€ "
            f"({active['improvement_vs_baseline_pct']:+.2f}%)."
        )
    else:
        reason = "Aucune restriction ne bat encore le baseline x20 avec robustesse suffisante."

    return {
        "mode": mode,
        "label": active["label"],
        "filters": active["filters"],
        "target": report["target"],
        "reason": reason,
        "summary": active["summary"],
        "baseline": baseline,
        "improvement_vs_baseline_pct": active["improvement_vs_baseline_pct"],
        "rules": report["rules"],
    }


def _current_paris_now(now=None):
    if now is not None:
        return now
    return tz.paris_now()


def current_session(asset, now=None):
    p = _current_paris_now(now)
    h, wd = p.hour, p.weekday()
    if wd >= 5:
        return "WEEKEND"
    if asset == "US500":
        if 15 <= h < 16:
            return "US_OPEN"
        if 16 <= h < 18:
            return "US_AM"
        if 18 <= h < 20:
            return "US_PM"
        if 20 <= h < 22:
            return "US_CLOSE"
        if 9 <= h < 15:
            return "EU_PREMARKET"
        return "OVERNIGHT"
    if 1 <= h < 9:
        return "ASIAN"
    if 9 <= h < 13:
        return "LONDON"
    if 13 <= h < 15:
        return "PRE_NY"
    if 15 <= h < 18:
        return "NY"
    if 18 <= h < 22:
        return "NY_PM"
    return "OVERNIGHT"


def matches_decision(decision, policy=None, now=None):
    if policy is None:
        policy = active_policy()
    if policy.get("mode") != "ACTIVE_FILTER":
        return {
            "accepted": True,
            "action": "ACCEPT",
            "policy_label": policy.get("label"),
            "reason": policy.get("reason"),
            "policy": policy,
        }

    setup = decision.get("setup") or {}
    asset = decision.get("asset") or setup.get("asset")
    filters = policy.get("filters") or {}
    checks = []

    if filters.get("asset"):
        checks.append(("asset", asset == filters["asset"]))
    if filters.get("direction"):
        checks.append(("direction", setup.get("direction") == filters["direction"]))
    if filters.get("strategy"):
        checks.append(("strategy", (setup.get("strategy") or "None") == filters["strategy"]))
    if filters.get("score_band"):
        checks.append(("score_band", _score_band(setup.get("conf") or setup.get("score")) == filters["score_band"]))
    if filters.get("session"):
        checks.append(("session", current_session(asset, now=now) == filters["session"]))
    if filters.get("hour_window"):
        p = _current_paris_now(now)
        hw = filters["hour_window"]
        checks.append(("hour_window", _hour_in_window(p.hour, hw["start"], hw["end"])))

    accepted = all(ok for _, ok in checks)
    if accepted:
        reason = f"setup conforme a la politique edge active {policy['label']}."
        action = "ACCEPT"
    else:
        failed = ", ".join(name for name, ok in checks if not ok)
        reason = f"hors politique edge active {policy['label']} ({failed})."
        action = "FILTER_OUT"

    return {
        "accepted": accepted,
        "action": action,
        "policy_label": policy.get("label"),
        "reason": reason,
        "policy": policy,
    }


def write_state(report):
    with open(STATE_FILE, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)


def main():
    report = evaluate()
    write_state(report)
    active = report["active"]
    baseline = report["baseline"]

    print("═" * 78)
    print("  ADAPTIVE EDGE, auto-evaluation x20")
    print("═" * 78)
    print(
        f"  Target {report['target']} | levier x{report['leverage']} | "
        f"risque compte cappe {report['account_risk_cap_pct']}% | capital depart {START_EQUITY:.0f}€"
    )
    print(
        f"  Baseline: {baseline['final_equity']}€ ({baseline['profit_pct']:+.2f}%) "
        f"DD {baseline['max_dd_pct']}% n={baseline['n']} decisive={baseline['decisive']}"
    )
    print(
        f"  Politique active: {active['label']} | final {active['summary']['final_equity']}€ "
        f"delta {active['improvement_vs_baseline_pct']:+.2f}% | "
        f"{'ACTIVE' if active['active_eligible'] else 'BASELINE'}"
    )
    print("\n  Top candidats")
    for c in report["top"][:10]:
        s = c["summary"]
        flag = "ACTIVE" if c["active_eligible"] else "watch"
        print(
            f"   {flag:6} {c['label']:<34} final {s['final_equity']:>8.2f}€ "
            f"delta {c['improvement_vs_baseline_pct']:>+6.2f}% DD {s['max_dd_pct']:>6.2f}% "
            f"n={s['n']:>2} dec={s['decisive']:>2} exp/trade {s['expectancy_account_pct']:+.3f}%"
        )
    print(f"\n  Etat ecrit: {STATE_FILE}")
    print("═" * 78)


if __name__ == "__main__":
    main()
