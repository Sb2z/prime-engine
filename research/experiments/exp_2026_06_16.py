#!/usr/bin/env python3
"""Expérience PRIME ANALYST du 2026-06-16 17h, slot evening.

UNE hypothèse NOUVELLE, falsifiable, données du lake (source homogène :
prix yfinance GC=F ; aucune 2e source mélangée). Exit fixé A PRIORI (aucun
paramètre retuné après résultat).

Contexte d'ingestion (cf. rapport analyst_2026-06-16_17h.md) :
  - Santé bot VERTE : watcher cycle 17:00, datafeed tradingview, gate
    apprentissage 840/500 (progresse depuis 754 à 13h), 0 outcome MIXED exclu
    (ret_4h reste corrigé), lab 18/17/0/0.
  - Autopsie 13h->17h : 3 signaux LONG (GOLD A_SETUP 13:03 entry 4333.78 ;
    US500 13:45 & 14:28 entry 7548.76), AUCUN rempli (prix retracé seulement
    jusqu'à 4338.8 / 7552.9 dans les fenêtres de validité 45 min) ; le réalisé
    a été baissier/plat -> les non-fills ont ÉVITÉ des longs perdants. Le
    forecast LONG a persisté en régime RANGE/TRANSITION/HACHÉE alors que le
    réalisé n'a pas suivi : confirme la conditionnalité de régime (HH/HI).

POURQUOI ce test (et pas un sweep) :
  HH (GOLD momentum_regime 1h, k6/thr0.5, exit TP 1.0%/stop 0.6%/h24) est mort
  PLAT : exp_net +0.0017 %, t 0.019, n 71. La thèse momentum dit que l'edge
  trend-day est dans la QUEUE DROITE, qu'un TP serré à 1.0 % tronque. L'exit
  n'entre PAS dans hypothesis_key (harness.py:65) : pour tester un exit
  "laisser courir" il FAUT une clé params distincte. Sam a élevé le 16/06 la
  priorité (a) [placement TP/RR par régime, maximiser l'espérance nette], ce test la tranche directement : un trigger plus sensible (k4/thr0.3, défauts
  famille, JAMAIS testés sur GOLD 1h) DANS le même régime trend propre
  (ER>=0.45/ADX>=30), avec un exit RR 2.5 (TP 2.0%/stop 0.8%/h48), relève-t-il
  l'espérance au-dessus du plat de HH ? Si NON (exp toujours ~0 quelle que soit
  la largeur de TP) -> le SIGNAL est le problème, pas l'exit : réoriente vers
  la famille momentum_breakout (entrée-marché, SPEC du 13h). variant_of=HH,
  déflation Bonferroni comprise (5e test famille -> z requis ~2.24+).

  n-faisabilité : k4/thr0.3 est PLUS permissif que k6/thr0.5, à travers le même
  filtre de régime 0.45/30 qui a déjà admis n=71 pour HH -> n >= 71, >> 30. OK.

NON TESTÉ ce soir, et POURQUOI :
  - ES=F même config : 2e test du compteur GLOBAL partagé avec le nocturne
    23h30 ; HI (ES, params HH) était déjà NÉGATIF -> probable kill, faible
    valeur marginale. Tenu en BACKLOG (le faire si le test GOLD surprend).
  - 15m intraday : absent du lake (1h/1d seulement) -> non adjudicable au juge,
    revalidation seulement en PAPER sur le feed de prod.
  - momentum_breakout (entrée-marché) : famille non encore ajoutée
    (strategy_families.py protégé) -> SPEC livrée au 13h, attend le token Sam.
"""

import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "research"))
import harness
import datalake


STRATEGIES = [
    {
        "id": "HL_gold_momentum_regime_runwinners",
        "hypothesis_text": "En régime de tendance propre (ER>=0.45/ADX>=30), un "
                           "trigger momentum plus sensible (k=4, thr=0.3) couplé à "
                           "un exit 'laisser courir' (TP 2.0%/stop 0.8%/48h, RR 2.5) "
                           "a une espérance nette POSITIVE sur l'or 1h, l'edge "
                           "trend-day vit dans la queue droite que le TP 1.0% serré "
                           "de HH tronquait (HH = exp plate +0.0017%).",
        "family": "momentum_regime",
        "params": {"k": 4, "thr_pct": 0.3, "er_min": 0.45, "adx_min": 30.0,
                   "er_n": 39, "adx_n": 14},
        "exit_rule": {"stop_pct": 0.8, "tp_pct": 2.0, "horizon_bars": 48},
        "assets": ["GOLD"], "timeframe": "1h",
        "variant_of": "HH_gold_momentum_regime_1h",
        "_lake": {"GOLD": "GC=F"},
    },
]


def main():
    for s in STRATEGIES:
        lake_map = s.pop("_lake")
        data, sources = {}, {}
        for asset, ticker in lake_map.items():
            candles, src = datalake.load_candles(ticker, s["timeframe"])
            data[asset] = candles
            sources[asset] = src
        r = harness.evaluate(s, data, sources=sources)
        print(f"\n{r['id']} -> {r['verdict']}")
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
