#!/usr/bin/env python3
"""Expérience PRIME ANALYST du 2026-06-17 13h, slot MIDDAY (focalisé, léger).

UNE hypothèse NOUVELLE, falsifiable, données du lake (source homogène :
prix yfinance GC=F 1d ; aucune 2e source mélangée).

Contexte d'ingestion (cf. rapport analyst_2026-06-17_13h.md) :
  - Santé bot VERTE : dernier cycle 12:59 Paris (frais <12 min), datafeed
    tradingview pur (6 flux), gate apprentissage 1240/500, 0 outcome MIXED,
    log propre, resim Gate-1 inchangé (USER WR 57.7% n=78 exp -0.001%).
    Lab 23/22/0/0 (dont 4 fixtures TEST_JUDGE).
  - JOUR FOMC : décision Fed 18:00 UTC (20:00 Paris) + dot plot + presser
    18:30 UTC ; US Retail Sales 12:30 UTC (14:30 Paris). Contexte = pré-FOMC,
    attentisme. Régime du jour 09h->13h : GOLD TRANSITION/RANGE (px +0.02%,
    PLAT), US500 RANGE/HACHÉE (px -0.23%), forecast US500 majoritairement
    SHORT/NEUTRAL. AUCUNE tendance propre. 43 cycles depuis 09h = 43 NO_TRADE
    sur les DEUX actifs. Le bot reste correctement à l'écart : le momentum
    intraday n'a RIEN à capter en chop pré-FOMC (thèse cohérente).

POURQUOI ce test, la DIMENSION HORIZON, jamais tranchée :
  Les 6 tests momentum_regime du registry (HH/HI/HL/HM/HP) ont TOUS été menés
  en INTRADAY 1h (GOLD et ES), avec divers knobs (k/thr/exit/ADX) -> tous
  KILLED, conclusion 09h : « le SIGNAL est limitant ». MAIS l'effet momentum
  documenté (Jegadeesh & Titman 1993, facteur UMD de Fama-French) est un
  phénomène à horizon MULTI-MOIS/SEMAINES, pas tick-à-tick. Question jamais
  posée au juge : et si l'edge momentum existe à son horizon NATIF (swing 1d)
  mais est NOYÉ intraday par le bruit + le coût de trading (qui frappe à chaque
  re-entrée) ? C'est LE diagnostic qui oriente toute la thèse intraday de Sam :
    - Si 1d PASSE le juge -> l'edge est HORIZON-DÉPLACÉ (swing, pas intraday) :
      signal majeur à Sam pour réorienter (ou n'utiliser l'intraday que pour le
      timing d'entrée d'un edge swing).
    - Si 1d est AUSSI plat/négatif net de coûts -> le « signal limitant » cesse
      d'être une propriété de l'intraday et devient vrai à TOUT horizon sur cet
      actif/période : la thèse momentum-sur-GOLD est close, pas seulement
      l'intraday. Résultat utile dans les deux sens.

  Isolement d'UNE dimension : config trigger EXACTE de HH (k6/thr0.5/ER0.45/
  ADX30) ; on change le TIMEFRAME 1h -> 1d. L'exit DOIT être re-mis à l'échelle
  du quotidien (24h != 24 jours) : il est fixé A PRIORI par la magnitude
  quotidienne mesurée (médiane |ret| 0.58%, p75 1.13%), PAS balayé :
    stop 1.2% (~p75 daily) / tp 2.4% / horizon 10 bars (~2 semaines de bourse).
  Aucun sweep d'exit -> aucun degré de liberté gagné. variant_of=HH.

  Faisabilité (probe) : 39 signaux bruts 1d sur 5 ans (2021-2026), 37 LONG /
  2 SHORT -> n_eff attendu ~30-39, >= 30. ATTENTION reconnue d'avance : 37L/2S
  sur une période de bull séculaire du gold (1800->4300) = échantillon
  fortement directionnel. La défense est le bootstrap PAR JOURS du harness :
  si les longs se concentrent en peu d'épisodes de tendance, l'IC s'élargit et
  le test ne passera pas. C'est exactement le garde-fou anti-artefact voulu.

  Déflation : 7e test de la famille momentum_regime -> z requis encore durci
  (~2.45, Bonferroni GLOBAL partagé avec le nocturne). Assumé : ce test TRANCHE
  la dimension horizon, restée vierge ; il n'est pas cosmétique.

  Non-doublon : hypothesis_key inclut params + timeframe (harness.py) ;
  {momentum_regime, GOLD, 1d} != tous les tests 1h existants -> clé NOUVELLE.
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
        "id": "HQ_gold_momentum_regime_1d_swing",
        "hypothesis_text": "Le momentum de tendance propre (ER>=0.45 ET ADX>=30, "
                           "trigger k=6/thr=0.5), KILLED 6x en INTRADAY 1h, dégage "
                           "une espérance nette POSITIVE à son horizon NATIF de swing "
                           "(GOLD 1d, exit stop1.2%/tp2.4%/10j), i.e. l'edge momentum "
                           "documenté (Jegadeesh-Titman) existe en daily mais est noyé "
                           "intraday par le bruit + le coût de re-entrée.",
        "family": "momentum_regime",
        "params": {"k": 6, "thr_pct": 0.5, "er_min": 0.45, "adx_min": 30.0},
        "exit_rule": {"stop_pct": 1.2, "tp_pct": 2.4, "horizon_bars": 10},
        "assets": ["GOLD"], "timeframe": "1d",
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
