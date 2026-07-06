#!/usr/bin/env python3
"""Expérience PRIME ANALYST du 2026-06-16 23h, slot evening.

UNE hypothèse NOUVELLE, falsifiable, données du lake (source homogène :
prix yfinance ES=F ; aucune 2e source mélangée). Exit fixé A PRIORI.

Contexte d'ingestion (cf. rapport analyst_2026-06-16_23h.md) :
  - Santé bot VERTE : watcher cycle 22:59 (frais <12 min), datafeed
    tradingview pur, gate apprentissage 970/500 (progresse depuis 840 à 17h,
    754 à 13h), 0 outcome MIXED exclu (ret_4h reste corrigé), lab 19/18/0/0.
  - Journée du bot : 485 NO_TRADE, 5 A_SETUP, 4 WATCH, TOUS LONG, sur une
    séance baissière/plate (GOLD 4347->4331, US500 7560->7508). Régimes
    dominants HACHÉE/RANGE/TRANSITION. Le forecast LONG a persisté toute la
    journée CONTRE le réalisé ; au dernier cycle 22:59 le forecast US500 a
    enfin basculé SHORT (15m -0.84 / 1h -0.68). Le filtre de régime trend
    (ER>=0.45/ADX>=30) aurait EXCLU l'essentiel de la journée -> protège.

POURQUOI ce test (et pas un sweep), clôture du backlog explicite du 17h :
  HL (GOLD momentum_regime 1h, k4/thr0.3, régime trend 0.45/30, exit
  "laisser courir" TP 2.0%/stop 0.8%/48h, RR 2.5) est mort sur SIGNIFICATIVITÉ
  (n=58, exp_net +0.1851%, IC95 (-0.112, 0.492), t=1.115 < z 2.241) mais
  l'estimation ponctuelle a SAUTÉ de +0.0017% (HH, TP serré 1.0%) à +0.185%
  (TP large 2.0%) -> le placement du TP COMPTE, l'edge trend-day vit dans la
  QUEUE DROITE qu'un TP serré tronque. Le 17h a explicitement mis ES=F en
  BACKLOG, conditionné à "si le test GOLD surprend" : il a surpris (x100 sur
  l'estimation ponctuelle). Ce test tranche la VALIDITÉ EXTERNE : la même
  config exit-large relève-t-elle l'espérance sur un 2e actif (US500/ES=F),
  avec un échantillon indépendant ? Si NON -> l'effet GOLD est probablement
  du bruit de queue spécifique, pas un edge généralisable -> réorienter vers
  momentum_breakout (entrée-marché, SPEC déjà livrée). Si OUI (positif, même
  sans significativité) -> faisceau convergent à 2 actifs pour priorité (a),
  candidat à approfondir (n agrégé, paper).

  Non-doublon : HI (ES, params HH = k6/thr0.5) était NÉGATIF, mais sa clé
  d'hypothèse diffère (k/thr entrent dans hypothesis_key, harness.py:65 ;
  l'exit n'y entre PAS). {momentum_regime, k4/thr0.3/er0.45/adx30, US500, 1h}
  N'A JAMAIS été soumis -> clé nouvelle. variant_of=HL (chaîne HH->HL->HM),
  déflation Bonferroni comprise (test famille suivant -> z requis ~2.3+).

  n-faisabilité : k4/thr0.3 est PLUS permissif que k6/thr0.5 (HI) à travers le
  même filtre 0.45/30 ; le régime trend est plus fréquent sur ES que GOLD ce
  cycle -> n attendu >= celui de HL (58), >> 30. OK.

UNE SEULE hypothèse ce soir, et POURQUOI pas 2 :
  Le compteur de déflation est GLOBAL et partagé avec le nocturne 23h30 ;
  chaque test durcit le z requis pour TOUS. Discipline (cf. autopsie 13h/17h) :
  pas de 2e test cosmétique. Un test de validité externe propre > deux tests
  dilués. Backlog 2e slot ci-dessous, non consommé.
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
        "id": "HM_us500_momentum_regime_runwinners",
        "hypothesis_text": "Validité externe de HL : en régime de tendance propre "
                           "(ER>=0.45/ADX>=30), un trigger momentum sensible "
                           "(k=4, thr=0.3) couplé à un exit 'laisser courir' "
                           "(TP 2.0%/stop 0.8%/48h, RR 2.5) a une espérance nette "
                           "POSITIVE sur l'US500 1h (ES=F), si l'edge queue-droite "
                           "vu sur l'or se généralise à un 2e actif, faisceau "
                           "convergent pour la priorité (a) placement du TP.",
        "family": "momentum_regime",
        "params": {"k": 4, "thr_pct": 0.3, "er_min": 0.45, "adx_min": 30.0,
                   "er_n": 39, "adx_n": 14},
        "exit_rule": {"stop_pct": 0.8, "tp_pct": 2.0, "horizon_bars": 48},
        "assets": ["US500"], "timeframe": "1h",
        "variant_of": "HL_gold_momentum_regime_runwinners",
        "_lake": {"US500": "ES=F"},
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
