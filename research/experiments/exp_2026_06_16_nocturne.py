#!/usr/bin/env python3
"""Expérience RESEARCH LAB nocturne du 2026-06-16 (slot 23h30 chercheur).

DEUX hypothèses NOUVELLES, falsifiables, données du lake (source homogène
par test : prix yfinance ; aucune 2e source mélangée). Exits fixés A PRIORI.

CONTEXTE D'INGESTION (cf. rapport 2026-06-16.md) :
  - Pas de research/PAUSE. Lake frais (GC=F/ES=F 1h = 13733/13695 barres,
    dernière bougie 2026-06-16T04:00Z). Harness/datalake/feature_store OK.
  - GATE APPRENTISSAGE FRANCHI : feature_store 975/500, apprentissage_autorise
    = TRUE (était 489 le 15/06, 72 figé avant). La source de mining "issues des
    A_SETUP/WATCH de Prime" (backlog #1 du 15/06) est OUVERTE. Mesure d'edge
    faite EN AMONT (probe, hors harness, cf. rapport §1) : sur la fenêtre
    disponible les signaux Prime sont 100% LONG (direction dégénérée sur une
    fenêtre baissière) -> A_SETUP ret_4h edge -0.021% IC95 (-0.223,-0.014)
    borne haute < 0 (NÉGATIF spécifique à la fenêtre), WATCH ret_4h +0.496%
    mais IC95 (-0.097, 0.846) à cheval sur 0 (n=42). Observationnel, PAS un
    verdict harness -> reste au rapport, pas au registry.
  - Familles existantes largement épuisées : momentum_regime 6 tests tous
    KILLED (z deflaté 2.39 ; l'analyste 23h conclut que le SIGNAL est le
    facteur limitant, pas l'exit -> ne pas re-tester), mean_reversion 2 KILLED,
    session_hour 2 KILLED, cot_extreme 2 KILLED + déflation à mort. ICHIMOKU :
    4 mécanismes réfutés (kumo_break HC, tk_cross HF, kijun_reject HG,
    chikou_confirm HJ, 2 nettement négatifs). RESTE UN SEUL mécanisme jamais
    testé : `twist`.

POURQUOI CES DEUX TESTS (pas un sweep) — clôture du backlog #2 du 15/06 :
  Le backlog demandait, AVANT de tester twist, de vérifier qu'il existe une
  raison spécifique de le croire DIFFÉRENT des 4 mécanismes déjà morts ; sinon
  déclarer Ichimoku clos. La raison existe et elle est conceptuelle, pas
  cosmétique : les 4 mécanismes réfutés sont des entrées DANS une tendance
  ÉTABLIE (cassure du nuage, croisement TK, rejet sur Kijun, confluence Chikou).
  `twist` est le SEUL qui capture le DÉBUT de tendance (changement de couleur
  du nuage connu à t, twist_age==1) : un régime d'edge potentiellement distinct
  (prise de tendance naissante vs continuation). C'est donc une hypothèse
  falsifiable propre, et le test qui FERME définitivement le périmètre Ichimoku.

  Validité externe pré-enregistrée (PAS un post-hoc) : si twist capte une
  amorce de tendance, l'effet doit se GÉNÉRALISER aux deux actifs capables de
  tendance du lake. On teste donc GOLD (HN) ET US500 (HO, variant_of=HN) la
  même nuit. La famille `ichimoku_twist` a 0 test antérieur au registry :
  HN est le test n°1 (z requis 1.645), HO le test n°2 après enregistrement de
  HN (z requis ~1.96) — la déflation Bonferroni s'applique DANS la nuit.

EXITS — AUCUN nouveau degré de liberté :
  On réutilise EXACTEMENT la convention de continuation Ichimoku héritée de
  HF/HG/HJ (stop 0.8 / tp 1.5 / horizon 48 barres, RR ~1.9). On NE retune PAS
  l'exit : l'analyste 23h a montré (lignée HH/HL/HM) que l'edge ne vit pas dans
  le placement du TP mais dans le signal -> introduire un exit "laisser courir"
  ici ne ferait qu'ajouter un degré de liberté de data mining. Exit identique
  = verdict directement COMPARABLE aux 4 autres mécanismes Ichimoku.

n-faisabilité : probe (hors harness) -> twist/standard génère 341 signaux GOLD
  et 324 US500 sur la série complète ; après fenêtres de test (3/4) et dédup
  une-position-à-la-fois, n_eff attendu >> 30 (pas de famine). OK.

SIGN-FLIP INTERDIT rappelé : si twist perd, son inverse n'est PAS une
conclusion. Direction LONG et SHORT déjà symétriques dans le signal lui-même.
"""

import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "research"))
import harness
import datalake

# Convention de continuation Ichimoku, identique à HF/HG/HJ — fixée a priori.
_ICHI_EXIT = {"stop_pct": 0.8, "tp_pct": 1.5, "horizon_bars": 48}

STRATEGIES = [
    {
        "id": "HN_gold_ichimoku_twist",
        "hypothesis_text": "Le twist du nuage Ichimoku (changement de couleur "
                           "connu à t, twist_age==1, prix du bon côté du nuage) "
                           "capte une AMORCE de tendance sur GOLD 1h et a une "
                           "espérance nette POSITIVE — mécanisme distinct des 4 "
                           "entrées de continuation déjà réfutées. Si vrai, c'est "
                           "le seul Ichimoku survivant ; si faux, le périmètre "
                           "Ichimoku est clos (5/5 mécanismes morts).",
        "family": "ichimoku_twist",
        "params": {"speed": "standard"},
        "exit_rule": dict(_ICHI_EXIT),
        "assets": ["GOLD"], "timeframe": "1h",
        "variant_of": None,
        "_lake": {"GOLD": "GC=F"},
    },
    {
        "id": "HO_us500_ichimoku_twist",
        "hypothesis_text": "Validité externe de HN : si le twist capte une amorce "
                           "de tendance, l'effet se GÉNÉRALISE à l'US500 1h "
                           "(ES=F) — espérance nette POSITIVE, même config/exit, "
                           "2e actif indépendant. variant_of=HN ; déflation "
                           "Bonferroni comprise (test famille n°2).",
        "family": "ichimoku_twist",
        "params": {"speed": "standard"},
        "exit_rule": dict(_ICHI_EXIT),
        "assets": ["US500"], "timeframe": "1h",
        "variant_of": "HN_gold_ichimoku_twist",
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
