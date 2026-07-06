#!/usr/bin/env python3
"""Résumé Prime watcher sur N jours.

Compte les cycles, A_SETUP/WATCH/NO_TRADE par actif, et les triggers uniques.
Usage:
  python3 prime_summary.py 7
"""

import collections
import datetime
import json
import sys

import clusters
import uncertainty

EVENTS_FILE = "/Users/sam/trading/prime_watcher_events.jsonl"


def parse_ts(value):
    return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_events(days):
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
    events = []
    try:
        with open(EVENTS_FILE) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    ts = parse_ts(event["ts"])
                except Exception:
                    continue
                if ts >= cutoff:
                    events.append(event)
    except FileNotFoundError:
        pass
    return events


def setup_key(decision):
    setup = decision.get("setup") or {}
    def bucket(value):
        try:
            return round(float(value), 1)
        except Exception:
            return value
    return "|".join(str(x) for x in (
        decision.get("asset"),
        setup.get("direction"),
        bucket(setup.get("entry")),
        bucket(setup.get("stop")),
        bucket(setup.get("tp")),
    ))


def summarize(days=7):
    events = load_events(days)
    cycles = [e for e in events if e.get("type") == "cycle"]
    triggers = [e for e in events if e.get("type") == "trigger"]
    errors = [e for e in events if e.get("type") == "error"]

    by_asset_grade = collections.defaultdict(collections.Counter)
    by_asset_forecast = collections.defaultdict(collections.Counter)
    unique_triggers = {}

    for event in cycles:
        for d in event.get("decisions") or []:
            asset = d.get("asset", "?")
            by_asset_grade[asset][d.get("grade", "?")] += 1
            by_asset_forecast[asset][d.get("forecast_direction", "?")] += 1

    for event in triggers:
        d = event.get("decision") or {}
        unique_triggers.setdefault(setup_key(d), event)

    return {
        "days": days,
        "events": len(events),
        "cycles": len(cycles),
        "triggers": len(triggers),
        "unique_triggers": list(unique_triggers.values()),
        "errors": errors,
        "by_asset_grade": by_asset_grade,
        "by_asset_forecast": by_asset_forecast,
    }


def main():
    days = 7
    if len(sys.argv) > 1:
        try:
            days = int(sys.argv[1])
        except Exception:
            pass
    s = summarize(days)
    print("═" * 66)
    print(f"  PRIME SUMMARY — derniers {s['days']} jours")
    print("═" * 66)
    print(f"  Cycles analysés: {s['cycles']} | triggers: {s['triggers']} | uniques: {len(s['unique_triggers'])} | erreurs: {len(s['errors'])}")
    for asset in sorted(s["by_asset_grade"]):
        grades = s["by_asset_grade"][asset]
        forecasts = s["by_asset_forecast"][asset]
        print(f"\n  {asset}")
        print("   grades   : " + " · ".join(f"{k}={v}" for k, v in grades.most_common()))
        print("   forecasts: " + " · ".join(f"{k}={v}" for k, v in forecasts.most_common()))
    print("\n  Stats journal (trades effectifs, doublons exclus, WR = TP/SL)")
    eff = clusters.effective_trades()
    for label, rows in (("IA", [t for t in eff if clusters.is_ai(t)]),
                        ("USER", [t for t in eff if not clusters.is_ai(t)])):
        wins = sum(t.get("result") == "WIN" for t in rows)
        losses = sum(t.get("result") == "LOSS" for t in rows)
        wr = round(wins / (wins + losses) * 100, 1) if wins + losses else None
        exp = round(sum(t.get("pnl_pct") or 0 for t in rows) / len(rows), 3) if rows else None
        ci = uncertainty.bootstrap_exp_by_day(rows)
        ci_txt = f" · exp IC95 [{ci[0]:+.3f}, {ci[1]:+.3f}]%" if ci else ""
        exp_txt = f"{exp:+.3f}%" if exp is not None else "?"
        print(f"   {label}: {uncertainty.fmt_wr(wr, wins, wins + losses)} "
              f"(effectif {len(rows)}) exp {exp_txt}{ci_txt}")

    if s["unique_triggers"]:
        print("\n  A_SETUP uniques")
        for event in s["unique_triggers"]:
            d = event.get("decision") or {}
            setup = d.get("setup") or {}
            print(
                f"   {event.get('paris')} {d.get('asset')} {setup.get('direction')} "
                f"entry {setup.get('entry')} stop {setup.get('stop')} tp {setup.get('tp')} "
                f"RR {setup.get('rr')}:1 conf {setup.get('conf')}/10"
            )
    print("═" * 66)


if __name__ == "__main__":
    main()
