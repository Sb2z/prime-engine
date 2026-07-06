#!/usr/bin/env python3
"""Expérience CHERCHEUR NOCTURNE du 2026-06-17 (slot 23h30, run nocturne).

TROIS hypothèses NOUVELLES, falsifiables. UN SEUL levier méthodologique neuf
cette nuit : le POOL MULTI-ACTIFS GOLD+ES sur l'horizon 1d.

POURQUOI ce levier — l'analyste a refermé l'horizon SWING 1d non pas sur un
verdict d'edge mais sur un MANQUE DE PUISSANCE : HQ (GOLD 1d momentum_regime)
exp +1.55% mais n_eff=12<30, HR (ES 1d) exp -0.40% n_eff=8<30. Les deux
KILLED « faute de n ». Le backlog #3 de l'analyste (23h) en tire : « le 1d ne
deviendra puissant qu'en agrégeant plusieurs instruments (n_eff>=30) — HORS
LAKE ACTUEL ; ne PAS sauver par sweep ».

  CORRECTION FACTUELLE : ce n'est PAS hors lake. Le lake contient GC=F ET ES=F
  en 1d, et `harness.evaluate` POOLE nativement les actifs d'un même `data`
  dict (boucle `for asset, candles in data.items()` dans chaque fenêtre,
  trades concaténés). La garde anti-basis n'interdit que les SOURCES
  hétérogènes — or GC=F et ES=F sont TOUS DEUX yfinance (une seule source).
  Pooler GOLD+ES n'est donc ni un sweep, ni un mélange de sources : c'est
  EXACTEMENT le remède de puissance que l'analyste a nommé, et il est IN-LAKE.

  Ce n'est pas non plus un data-mining d'actif : GOLD et US500 sont les DEUX
  SEULS actifs que Sam trade (mapping protocole). On n'élargit pas vers DXY/VIX/
  ZN (non tradés) pour pêcher un survivant — on agrège uniquement les deux
  actifs cibles, ce qui répond à la question « la règle 1d généralise-t-elle
  sur MES deux actifs, et ce une fois la puissance suffisante ? ».

ISOLEMENT DES DEGRÉS DE LIBERTÉ — aucun paramètre inventé cette nuit :
  - Trigger momentum_regime (HU) : k6/thr0.5/ER0.45/ADX30 = EXACTEMENT HQ/HR.
  - Trigger momentum_breakout (HV) : lookback20/ER0.45/ADX30 = EXACTEMENT HS/HT.
  - Trigger mean_reversion (HW) : k6/thr1.0 = EXACTEMENT H2/HK (seul le
    timeframe passe de 1h à 1d : on change UNE dimension, l'horizon).
  - Exit 1d UNIQUE pour les trois : stop1.2/tp2.4/10 = le SEUL exit 1d déjà
    calibré du lab (HQ/HR). Zéro nouveau degré de liberté d'exit sur la nuit.
  La SEULE chose neuve = `assets=["GOLD","US500"]` pooled. Tout le reste hérité.

LECTURE ATTENDUE (utile dans tous les cas) :
  - HU/HV restent n_eff<30 même poolés -> le 1d est si sélectif (gate ER/ADX
    quotidien) que 2 actifs ne suffisent pas : le seul chemin honnête est PLUS
    d'instruments / un historique plus long, PAS un sweep. Referme le 1d
    proprement (corrige « hors lake » -> « in-lake mais encore sous-puissant »).
  - HU pooled dilue le +1.55% de HQ avec l'échantillon bear-inclus d'ES : si
    l'exp s'effondre (-> ~+0.7% ou moins) ET reste non significative, ça
    CORROBORE que le +1.55% de HQ était le BULL DU GOLD, pas un edge momentum.
  - HW (mean_reversion 1d, SANS gate) est le seul bien-powered (n_eff>>30) :
    teste la thèse classique « surréaction quotidienne -> réversion » sur les
    deux actifs de Sam. Premier vrai verdict 1d non limité par la puissance.
  - Si l'un PASSE (IC_bas>0, t>=z, n_eff>=30, 2/3 fen.+) -> signal à Sam.
    Attendu : KILLED (mortalité >90% = santé ; le 1d est probablement mort
    aussi, mais cette fois MESURÉ, pas supposé).

SIGN-FLIP / SWEEP : aucun. Triggers tous hérités, exits hérités, aucune
  reformulation après résultat. variant_of déclaré pour chaque (HQ/HS/H2).
  Non-doublon : hypothesis_key = hash(family, params, sorted(assets), tf) ;
  assets=["GOLD","US500"] (pooled) != HQ/HR (mono-actif) et != H2/HK (1h)
  -> clés NOUVELLES.

Contexte d'ingestion (cf. analyst_2026-06-17_23h.md, ré-vérifié ce run) :
  - resim Gate-1 USER inchangé (WR 57.7% n=78 exp -0.001%, récent 8<15 décisifs).
  - feature_store gate 1457/500 (apprentissage_autorise=true, 0 MIXED).
  - Lake yfinance frais (refresh 17/06 07:00). Lab AVANT run : 27/26/0/0
    (dont 4 fixtures TEST_JUDGE). Pas de research/PAUSE.

Déflation (Bonferroni à vie, par famille, partagée avec l'analyste) :
  - HU momentum_regime = 9e test famille -> z ~2.54 (barre haute, assumée :
    HU TRANCHE la puissance laissée ouverte par HQ/HR, non cosmétique).
  - HV momentum_breakout = 3e test -> z ~2.13.
  - HW mean_reversion = 3e test -> z ~2.13.
"""

import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "research"))
import harness
import datalake

# Pool des deux actifs cibles, source homogène (yfinance), horizon 1d.
_POOL = {"GOLD": "GC=F", "US500": "ES=F"}
_EXIT_1D = {"stop_pct": 1.2, "tp_pct": 2.4, "horizon_bars": 10}  # hérité HQ/HR

STRATEGIES = [
    {
        "id": "HU_pool_momentum_regime_1d",
        "hypothesis_text": "Le momentum_regime 1d (trigger k6/thr0.5/ER0.45/ADX30, "
                           "exit stop1.2/tp2.4/10 — EXACTEMENT HQ/HR) POOLÉ sur "
                           "GOLD+ES atteint-il enfin la puissance (n_eff>=30) que "
                           "HQ(n12)/HR(n8) n'avaient pas, et l'exp survit-elle une "
                           "fois le +1.55% du seul GOLD dilué par l'échantillon "
                           "bear-inclus d'ES ? Si exp s'effondre et reste non "
                           "significative, HQ était le bull du gold, pas un edge.",
        "family": "momentum_regime",
        "params": {"k": 6, "thr_pct": 0.5, "er_min": 0.45, "adx_min": 30.0},
        "exit_rule": dict(_EXIT_1D),
        "assets": ["GOLD", "US500"], "timeframe": "1d",
        "variant_of": "HQ_gold_momentum_regime_1d_swing",
        "_lake": dict(_POOL),
    },
    {
        "id": "HV_pool_momentum_breakout_1d",
        "hypothesis_text": "Le momentum_breakout 1d (cassure Donchian20 + gate "
                           "ER0.45/ADX30 — EXACTEMENT HS/HT, exit 1d stop1.2/tp2.4/10) "
                           "POOLÉ GOLD+ES : le breakout, plat net de coûts en 1h "
                           "(HS/HT), dégage-t-il un edge à l'horizon SWING 1d une "
                           "fois poolé pour la puissance ? Symétrique de HU pour "
                           "l'autre mécanisme d'entrée (déclenchement vs persistance).",
        "family": "momentum_breakout",
        "params": {"lookback": 20, "er_min": 0.45, "adx_min": 30.0},
        "exit_rule": dict(_EXIT_1D),
        "assets": ["GOLD", "US500"], "timeframe": "1d",
        "variant_of": "HS_gold_momentum_breakout_1h",
        "_lake": dict(_POOL),
    },
    {
        "id": "HW_pool_mean_reversion_1d",
        "hypothesis_text": "La mean_reversion (trigger k6/thr1.0 — EXACTEMENT H2/HK, "
                           "seul l'horizon passe de 1h à 1d ; exit 1d stop1.2/tp2.4/10) "
                           "POOLÉE GOLD+ES : la surréaction QUOTIDIENNE (mouvement "
                           "6 jours >1%) réverse-t-elle net de coûts ? Famille SANS "
                           "gate -> seule des trois bien-powered (n_eff>>30) : 1er "
                           "vrai verdict 1d non limité par la puissance. Réversion "
                           "1h morte (H2 -0.065%, HK -0.039%) ; le 1d est-il différent ?",
        "family": "mean_reversion",
        "params": {"k": 6, "thr_pct": 1.0},
        "exit_rule": dict(_EXIT_1D),
        "assets": ["GOLD", "US500"], "timeframe": "1d",
        "variant_of": "H2_es_meanrev_1pct",
        "_lake": dict(_POOL),
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
