#!/usr/bin/env python3
"""Expérience PRIME ANALYST du 2026-06-17 09h, slot matin (focalisé).

UNE hypothèse NOUVELLE, falsifiable, données du lake (source homogène :
prix yfinance GC=F ; aucune 2e source mélangée). Exit fixé A PRIORI, IDENTIQUE à HH (aucun nouveau degré de liberté d'exit).

Contexte d'ingestion (cf. rapport analyst_2026-06-17_09h.md) :
  - Santé bot VERTE : dernier cycle 08:56 Paris (frais <12 min), datafeed
    tradingview pur (6 flux), gate apprentissage 1154/500 (975 hier soir),
    0 outcome MIXED exclu, log propre, resim Gate-1 inchangé (USER WR 57.7%
    n=78 exp -0.001%). Lab 22/21/0/0 (dont 4 fixtures).
  - Matinée du bot (00:01->08:56, 96 cycles) : 96 NO_TRADE sur les DEUX
    actifs. GOLD régime RANGE(69)/TRANSITION(27), px -0.07% (plat). US500
    HACHÉE(44)/TRANSITION(30)/RANGE(18)/MOYENNE(4), px +0.25%. AUCUNE
    tendance propre ce matin -> le bot reste correctement à l'écart ; le
    momentum n'avait RIEN à capter (thèse cohérente : il faut de la tendance).
  - Reconduction edge Prime (report-only, backlog #1) : A_SETUP/WATCH
    TOUJOURS 100% LONG (direction dégénérée), ~2-3 jours distincts seulement
    -> NON concluant, inchangé depuis hier. Pas de conclusion.

POURQUOI ce test, clôture du DERNIER levier de régime non exploré :
  Le faisceau HH/HL/HM (analyste 23h) conclut « le SIGNAL momentum_regime est
  limitant, pas l'exit », mais cette inférence a été établie en faisant varier
  k/thr/exit À PORTE DE RÉGIME FIXE (ER>=0.45/ADX>=30). La dimension
  RÉGIME-STRICTESSE, « et si le plancher ADX 30 admet encore trop de chop ? », n'a JAMAIS été testée (backlog #2 explicite du 23h : "seuil ADX plus
  exigeant"). Sur la priorité (b) du protocole (« entrée en régime tendanciel,
  ADX/ER ÉLEVÉ »), c'est LE levier à trancher. La matinée RANGE/HACHÉE rend la
  question naturelle : isoler UNIQUEMENT les bougies de tendance la plus propre
  sauve-t-il le momentum, ou le tue-t-il aussi ?

  Isolement d'UNE variable : on prend la config EXACTE de HH (k6/thr0.5,
  exit stop0.6/tp1.0/horizon24, GOLD 1h) et on ne change QUE adx_min 30->40.
  HH (adx30) était PLAT (+0.0017%). Comparaison directe -> variant_of=HH.
  - Si l'estimation ponctuelle SAUTE positive (comme l'exit l'avait fait sur
    HL) ET passe les checks (z déflaté ~2.39, IC_low>0, 2/3 fen.) -> vrai lead,
    candidat paper. Peu probable, mais à mesurer, pas à présumer.
  - Si elle reste plate/négative -> le "signal limitant" cesse d'être une
    inférence et devient un RÉSULTAT testé sur la dimension régime-strictesse :
    ni la sensibilité du trigger, ni l'exit, ni la STRICTESSE du filtre de
    tendance ne rendent momentum_regime rentable. Clôt proprement la piste.

  Non-doublon : hypothesis_key inclut params complet (harness.py:65) ;
  {momentum_regime, k6/thr0.5/er0.45/ADX40, GOLD, 1h} != HH (ADX30) -> clé
  NOUVELLE, jamais soumise. n-faisabilité vérifiée (probe) : 256 signaux bruts
  à ADX>=40 vs 307 à ADX>=30 -> n_eff attendu comparable à HH, >> 30.

  Déflation : 6e test de la famille momentum_regime -> z requis durci
  (~2.39, Bonferroni GLOBAL partagé avec le nocturne 23h30). Assumé : ce test
  TRANCHE le dernier levier de régime, il n'est pas cosmétique.

UNE SEULE hypothèse (slot matin focalisé) :
  Le 2e levier listé au backlog 23h, "momentum_regime + confluence
  session_hour", est en réalité INEXPRIMABLE dans la famille existante :
  _momentum_regime n'utilise PAS `ctx` (strategy_families.py:138), donc aucune
  confluence de session n'est passable par params/ctx. -> DÉCRIT comme SPEC
  pour Sam dans le rapport (fichier protégé, token requis), PAS testé en hack.
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
        "id": "HP_gold_momentum_regime_strictADX",
        "hypothesis_text": "En isolant UNIQUEMENT les bougies de tendance la plus "
                           "propre (porte stricte ER>=0.45 ET ADX>=40, vs le plancher "
                           "30 de HH), le MÊME trigger momentum (k=6, thr=0.5) et le "
                           "MÊME exit (stop 0.6%/tp 1.0%/24h) dégagent une espérance "
                           "nette POSITIVE sur GOLD 1h, i.e. le plancher ADX 30 "
                           "admettait trop de chop diluant l'edge trend-day.",
        "family": "momentum_regime",
        "params": {"k": 6, "thr_pct": 0.5, "er_min": 0.45, "adx_min": 40.0},
        "exit_rule": {"stop_pct": 0.6, "tp_pct": 1.0, "horizon_bars": 24},
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
