#!/usr/bin/env python3
"""Expériences du 12/06/2026 — run n°2 (nocturne automatique, 1re session
qui DÉMARRE réellement après les échecs de spawn des 10-11/06).

NOTE D'EXÉCUTION : la session chercheur a été lancée en mode headless
(`claude -p ... --permission-mode acceptEdits`, stdin fermé). Dans ce mode,
les écritures de fichiers sont auto-approuvées mais AUCUNE commande Bash ne
l'est (allowlist = `crontab -l` seulement). harness.evaluate() n'a donc PAS
pu être exécuté cette nuit. Ce fichier est prêt à tourner : une seule
approbation `python research/experiments/exp_2026_06_12.py` (ou l'ajout de
`Bash(python:*)` à .claude/settings.local.json) produit les 3 verdicts.
Tant qu'il n'a pas tourné, AUCUNE de ces hypothèses n'est dans le registry —
c'est voulu : pas de verdict sans le juge.

Trois hypothèses NOUVELLES, falsifiables, données lake yfinance horaire
(~2 ans), source homogène par test, mapping production GOLD↔GC=F.

HA (momentum_regime, variant_of=H1_gold_momentum_6h) :
    "Le momentum ±0.5%/6h sur l'or ne continue de façon nette de coûts QUE
     lorsque le régime est tendanciel (ER≥0.45 ET ADX≥30) ; le filtre de
     régime transforme l'edge NUL de H1 (inconditionnel, KILLED 10/06) en
     edge positif." — backlog #1, conditionnalité de régime explicite.

HB (session_hour) :
    "L'or dérive à la HAUSSE pendant la session OVERNIGHT (23h-08h Paris) —
     anomalie documentée du rendement overnight des métaux." Direction LONG
     choisie A PRIORI (littérature), pas après résultat — pas un sign-flip.
     Backlog #3, version prior-fondée plutôt que 'SHORT overnight' réactif.

HC (ichimoku_kumo_break) :
    "Une clôture 1h qui CASSE le nuage Ichimoku sur l'or continue dans le
     sens de la cassure (entrée de tendance canonique)." Première mise à
     l'épreuve de la famille ichimoku (approuvée 11/06), sur l'actif le plus
     tendanciel du lab. Périmètre fermé : speed 'standard', aucun paramètre
     libre.
"""

import json
import sys

sys.path.insert(0, "/Users/sam/trading")
sys.path.insert(0, "/Users/sam/trading/research")
import harness
import datalake

STRATEGIES = [
    {
        "id": "HA_gold_momentum_regime",
        "hypothesis_text": "Le momentum ±0.5%/6h sur l'or ne continue net de "
                           "coûts QUE en régime tendanciel (ER>=0.45 et "
                           "ADX>=30) — filtre de régime sur l'edge nul de H1.",
        "family": "momentum_regime",
        "variant_of": "H1_gold_momentum_6h",
        "params": {"k": 6, "thr_pct": 0.5, "er_min": 0.45, "adx_min": 30.0,
                   "er_n": 39, "adx_n": 14},
        "exit_rule": {"stop_pct": 0.6, "tp_pct": 1.0, "horizon_bars": 24},
        "assets": ["GOLD"], "timeframe": "1h",
        "_lake": {"GOLD": "GC=F"},
    },
    {
        "id": "HB_gold_overnight_drift",
        "hypothesis_text": "L'or dérive à la hausse en session OVERNIGHT "
                           "(23h-08h Paris) — anomalie du rendement overnight "
                           "des métaux (direction LONG fixée a priori).",
        "family": "session_hour",
        "params": {"start": 23, "end": 8, "direction": "LONG"},
        "exit_rule": {"stop_pct": 0.5, "tp_pct": 0.7, "horizon_bars": 8},
        "assets": ["GOLD"], "timeframe": "1h",
        "_lake": {"GOLD": "GC=F"},
    },
    {
        "id": "HC_gold_kumo_break",
        "hypothesis_text": "Une clôture 1h qui casse le nuage Ichimoku sur "
                           "l'or continue dans le sens de la cassure "
                           "(speed standard, périmètre fermé).",
        "family": "ichimoku_kumo_break",
        "params": {"speed": "standard"},
        "exit_rule": {"stop_pct": 0.8, "tp_pct": 1.5, "horizon_bars": 48},
        "assets": ["GOLD"], "timeframe": "1h",
        "_lake": {"GOLD": "GC=F"},
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
                  f"IC95={r['ci95_bootstrap_days']} t={r['t_stat']} "
                  f"z_requis={r['z_required']} "
                  f"(test famille n°{r['family_tests_lifetime']})")
            print(f"  fenêtres: {[(w['n'], w['exp']) for w in r['per_window']]}")
            print(f"  checks: {r['checks']}")
        else:
            print(f"  {r.get('note')}")
    print(f"\nCompteurs lab: "
          f"{json.dumps(harness.lab_counters(), ensure_ascii=False)}")


if __name__ == "__main__":
    main()
