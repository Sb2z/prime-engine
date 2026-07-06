#!/usr/bin/env python3
"""Expérience PRIME ANALYST du 2026-06-17 17h, slot EVENING (bilan séance).

UNE hypothèse NOUVELLE, falsifiable, données du lake (source homogène :
prix yfinance ES=F 1d ; aucune 2e source mélangée).

Contexte d'ingestion (cf. rapport analyst_2026-06-17_17h.md) :
  - Santé bot VERTE : dernier cycle 16:58 Paris (frais <12 min), datafeed
    tradingview pur (6 flux), gate apprentissage 1324/500, 0 outcome MIXED,
    log propre, resim Gate-1 inchangé (USER WR 57.7% n=78 exp -0.001%).
    Lab 24/23/0/0 (dont 4 fixtures TEST_JUDGE).
  - JOUR FOMC : décision Fed 18:00 UTC (20:00 Paris) + dot plot + presser
    18:30 UTC ; séance ENTIÈRE pré-FOMC (ce slot 17h précède la décision de 3h).
    Régime 13h->17h : GOLD RANGE (px ~4330->4345, plat), US500 TENDANCE HACHÉE
    (px ~7518->7500, -0.2%, forecast SHORT persistant). AUCUNE tendance propre.
    Cycles depuis 13h = NO_TRADE sur les DEUX actifs. Bot correctement à
    l'écart : rien à capter en attentisme pré-FOMC (thèse cohérente).

POURQUOI ce test, backlog #1 du 13h, l'OUT-OF-SAMPLE qui attaque le confound :
  HQ (13h) a montré le PREMIER momentum_regime du registry à passer 3/4 checks
  à horizon SWING 1d (GOLD : exp +1.55% net, t 3.70 > z 2.45, IC95 (0.66,2.32),
  fenêtres 0/+0.86/+1.90), KILLED uniquement sur n_eff=12<30. MAIS artefact
  reconnu d'avance : 37 LONG / 2 SHORT sur 5 ans de BULL SÉCULAIRE du gold
  (1800->4300). L'espérance positive PEUT ÊTRE le bull, pas un edge momentum
  généralisable ; n_eff=12 trop fin pour trancher.

  Le diagnostic décisif n'est PAS « plus de calcul sur GOLD » mais un AUTRE
  ACTIF où le momentum_regime 1d doit ré-apparaître S'IL est un edge réel et
  non le drift haussier d'un seul instrument. ES=F est le bon candidat :
    - sur 2021-2026 il monte (4222->7605, +80%) MAIS a connu le BEAR 2022
      (~-25% pic-creux) -> la porte de tendance ER45/ADX30 y tire AUSSI des
      SHORT (régime baissier propre), pas seulement des LONG. Diversité
      directionnelle qu'on n'a PAS sur le gold -> sépare edge momentum vs bull.
    - source homogène US500<->ES=F (convention HI/HM du registry).

  Isolement d'UNE dimension vs HQ : on change l'ACTIF (GOLD->ES), TOUT le
  reste identique. Trigger EXACT de HH/HQ (k6/thr0.5/ER0.45/ADX30). Exit
  RÉUTILISÉ TEL QUEL de HQ (stop1.2%/tp2.4%/10 bars) -> AUCUN nouveau degré
  de liberté : la magnitude quotidienne d'ES (median |ret| 0.558%, p75 1.055%,
  p90 1.682%) est quasi identique à celle du gold (median 0.58%, p75 1.13%) qui
  avait dimensionné l'exit de HQ -> le MÊME exit s'applique a priori, PAS de
  re-tuning, PAS de sweep. variant_of=HQ_gold_momentum_regime_1d_swing.

  Lecture attendue, utile dans les DEUX sens :
    - Si ES 1d PASSE aussi (IC>0, t>=z, n_eff>=30) -> l'edge momentum-swing est
      CROSS-ASSET, donc PAS un simple bull du gold : signal MAJEUR à Sam pour
      réorienter la thèse vers le swing (l'intraday ne servant qu'au timing).
    - Si ES 1d est plat/négatif net de coûts -> le +1.55% de HQ était très
      probablement le BULL DU GOLD, pas un edge momentum généralisable :
      la dimension horizon se referme aussi, le « signal limitant » vaut à
      tout horizon. Résultat tout aussi utile (referme une fausse piste).

  Déflation : 8e test de la famille momentum_regime -> z requis encore durci
  (Bonferroni GLOBAL partagé avec le nocturne). Assumé : ce test TRANCHE le
  confound bull-vs-edge laissé ouvert par HQ ; il n'est pas cosmétique.

  Non-doublon : hypothesis_key inclut params + asset + timeframe (harness.py) ;
  {momentum_regime, US500, 1d} != HI (US500,1h) et != HQ (GOLD,1d) -> NOUVELLE.
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
        "id": "HR_es_momentum_regime_1d_swing",
        "hypothesis_text": "Le momentum_regime à horizon SWING 1d (ER>=0.45 ET "
                           "ADX>=30, trigger k=6/thr=0.5, exit stop1.2%/tp2.4%/10j "
                           "identique à HQ), qui a passé 3/4 checks sur GOLD 1d "
                           "(KILLED sur n_eff=12), RÉAPPARAÎT sur ES=F 1d s'il "
                           "s'agit d'un edge momentum réel et non du seul bull "
                           "séculaire du gold ; ES a connu le bear 2022 (SHORT "
                           "propres) -> diversité directionnelle qui sépare edge "
                           "vs drift. S'il est plat sur ES, le +1.55% de HQ était "
                           "le bull du gold.",
        "family": "momentum_regime",
        "params": {"k": 6, "thr_pct": 0.5, "er_min": 0.45, "adx_min": 30.0},
        "exit_rule": {"stop_pct": 1.2, "tp_pct": 2.4, "horizon_bars": 10},
        "assets": ["US500"], "timeframe": "1d",
        "variant_of": "HQ_gold_momentum_regime_1d_swing",
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
