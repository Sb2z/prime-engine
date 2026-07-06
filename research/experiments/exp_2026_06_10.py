#!/usr/bin/env python3
"""Expériences du 10/06/2026, premier run (manuel, supervisé par Sam).

Trois hypothèses falsifiables, données lake yfinance horaire (~2 ans),
mapping production GOLD↔GC=F, US500↔ES=F. Source homogène par test.

H1 (momentum)        : "Un mouvement net de ±0.5% sur 6h sur l'or CONTINUE
                        dans son sens", l'edge trend-day de Sam, version
                        systématique grossière.
H2 (mean_reversion)  : "Un excès intraday de ±1% sur 6h sur l'ES REVIENT
                        vers sa moyenne", l'effet le plus documenté sur
                        indices en intraday.
H3 (session_hour)    : "Être LONG US500 pendant l'ouverture US (15-17h
                        Paris) a une espérance positive", drift
                        d'ouverture, saisonnalité de session.
"""

import json
import sys

sys.path.insert(0, "/Users/sam/trading")
sys.path.insert(0, "/Users/sam/trading/research")
import harness
import datalake

STRATEGIES = [
    {
        "id": "H1_gold_momentum_6h",
        "hypothesis_text": "Un mouvement net de ±0.5% sur 6 bougies 1h sur "
                           "l'or continue dans son sens (futures GC, 2 ans).",
        "family": "momentum",
        "params": {"k": 6, "thr_pct": 0.5},
        "exit_rule": {"stop_pct": 0.6, "tp_pct": 1.0, "horizon_bars": 24},
        "assets": ["GOLD"], "timeframe": "1h",
        "_lake": {"GOLD": "GC=F"},
    },
    {
        "id": "H2_es_meanrev_1pct",
        "hypothesis_text": "Un excès de ±1% sur 6 bougies 1h sur l'ES "
                           "mean-reverte (fade de l'excès, 2 ans).",
        "family": "mean_reversion",
        "params": {"k": 6, "thr_pct": 1.0},
        "exit_rule": {"stop_pct": 0.5, "tp_pct": 0.8, "horizon_bars": 16},
        "assets": ["US500"], "timeframe": "1h",
        "_lake": {"US500": "ES=F"},
    },
    {
        "id": "H3_us500_open_drift",
        "hypothesis_text": "Être LONG US500 pendant l'ouverture US "
                           "(15-17h Paris) a une espérance nette positive.",
        "family": "session_hour",
        "params": {"start": 15, "end": 17, "direction": "LONG"},
        "exit_rule": {"stop_pct": 0.4, "tp_pct": 0.6, "horizon_bars": 8},
        "assets": ["US500"], "timeframe": "1h",
        "_lake": {"US500": "ES=F"},
    },
]


def main():
    results = []
    for s in STRATEGIES:
        lake_map = s.pop("_lake")
        data, sources = {}, {}
        for asset, ticker in lake_map.items():
            candles, src = datalake.load_candles(ticker, s["timeframe"])
            data[asset] = candles
            sources[asset] = src
        r = harness.evaluate(s, data, sources=sources)
        results.append(r)
        print(f"\n{r['id']} → {r['verdict']}")
        if r["verdict"] in ("PAPER", "KILLED"):
            print(f"  n_eff={r['n_eff']} exp_net={r['expectancy_net']}% "
                  f"IC95={r['ci95_bootstrap_days']} t={r['t_stat']} z_requis={r['z_required']}"
                  f" (test famille n°{r['family_tests_lifetime']})")
            print(f"  fenêtres: {[(w['n'], w['exp']) for w in r['per_window']]}")
            print(f"  checks: {r['checks']}")
        else:
            print(f"  {r.get('note')}")
    print(f"\nCompteurs lab: {json.dumps(harness.lab_counters(), ensure_ascii=False)}")


if __name__ == "__main__":
    main()
