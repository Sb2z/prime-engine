#!/usr/bin/env python3
"""Expérience PRIME ANALYST du 2026-06-18 09h, slot MATIN (focalisé, léger).

DEUX hypothèses NOUVELLES, falsifiables, données du lake (source HOMOGÈNE par
test : GOLD↔GC=F 1d et US500↔ES=F 1d, jamais mélangées dans un même test).

Contexte d'ingestion (cf. rapport analyst_2026-06-18_09h.md) :
  - Santé bot VERTE : dernier cycle 09:00 Paris (frais), datafeed tradingview
    pur (6 flux), gate apprentissage 1634/500 (+181 depuis 23h), ret_4h se
    remplit (0 MIXED), watchdog vivant (state 08:54), Telegram 0 échec, log
    propre. Lab 30/29/0/0. resim Gate-1 inchangé (USER WR 57.7% n=78).
  - Régime du jour 00h→09h : GOLD TRANSITION (80/100 cycles) + HACHÉE/RANGE ;
    US500 HACHÉE/TRANSITION/RANGE. AUCUNE tendance propre. 100 cycles = 100
    NO_TRADE sur les DEUX actifs (post-FOMC, risk-off résiduel, forecast oscille
    LONG/SHORT/NEUTRAL sans conviction). Le bot reste correctement à l'écart :
    en chop le momentum intraday n'a rien à capter (thèse cohérente).
  - Macro du jour : BoE 11:00 UTC (décision taux, GBP, secondaire GOLD/US500),
    Philly Fed + Unemployment Claims 12:30 UTC. SNB déjà passée (07:30-08:00).

POURQUOI ces tests, ISOLER « signal momentum » vs « filtre de régime », et
GAGNER DE LA PUISSANCE, sur le seul horizon où subsiste un résidu (le 1d) :

  L'arc momentum_regime 1d est essentiellement CLOS mais pour une raison de
  PUISSANCE, pas d'edge tranché :
    - HQ (GOLD 1d, ER≥0.45 & ADX≥30) : exp +1.55%, IC95 [0.66, 2.32] (borne
      basse POSITIVE), t=3.698, mais n_eff=12 < 30 → KILLED sur la PUISSANCE,
      et confond bull-gold séculaire suspectée (37 LONG / 2 SHORT).
    - HR (ES 1d, même filtre) : exp −0.40%, IC95 [-1.30, 0.92], n_eff=8 → le
      résidu DISPARAÎT sur le contrôle ES (pas de tailwind bull-gold).
    - HU (poolé GOLD+ES 1d) : +1.55%→+0.77%, IC95 [0.037, 1.50], n_eff=20 →
      KILLED sur la puissance ; ES DILUE l'edge gold = edge gold-spécifique.

  MUR STRUCTUREL identifié : le filtre ER≥0.45 ET ADX≥30 est si sélectif sur
  des bougies QUOTIDIENNES qu'il ne produit JAMAIS n≥30 sur 5 ans / 1 actif
  (8-20 signaux) → aucune des variantes filtrées ne pourra PASSER la puissance,
  quelle que soit la valeur des knobs. Continuer à sweeper le filtre = cosmétique
  qui durcit Bonferroni pour tout le monde. Il faut changer de DIMENSION.

  La dimension vierge : RETIRER le filtre de régime. Le momentum INCONDITIONNEL
  au quotidien (time-series momentum, Moskowitz-Ooi-Pedersen 2012) n'a JAMAIS
  été soumis au juge au 1d (registry : H1 était momentum 6h intraday ; aucun
  {momentum, *, 1d}). Le retirer fait DEUX choses d'un coup :
    1. PUISSANCE : ~1045 signaux/actif (probe) au lieu de 8-20 → n_eff >> 30,
       le test TRANCHE enfin sur l'edge, plus sur l'échantillon.
    2. DÉCOMPOSITION : isole l'ingrédient actif. Si l'inconditionnel 1d est
       POSITIF net de coûts → le filtre ER/ADX n'était PAS l'ingrédient (juste
       du momentum daily) ; s'il est PLAT/négatif → le filtre concentrait un
       résidu réel (mais alors non-powerable, cf. mur ci-dessus).
    3. ÉQUILIBRE DIRECTIONNEL : 607L/438S (GOLD), 619L/424S (ES), bien plus
       symétrique que 37L/2S → désamorce partiellement la confond bull-gold
       (l'edge ne peut plus venir QUE des longs).

  CONTRÔLE par PAIRE (comme HQ↔HR) :
    - HX = GOLD 1d inconditionnel ; HY = ES 1d inconditionnel. Sources HOMOGÈNES
      séparées (aucun pool). Lecture croisée :
        * HX PASSE & HY PASSE → time-series momentum réel au daily, NON
          gold-spécifique : signal MAJEUR à Sam (réorienter vers le swing).
        * HX PASSE & HY échoue → artefact beta-gold (bull séculaire), la thèse
          momentum-sur-gold daily est de la BÊTA passive, pas de l'alpha. Mort.
        * Les deux échouent → momentum CLOS au 1d aussi (pas seulement intraday).
      Résultat informatif dans les TROIS cas, aucun n'est un échec.

  ISOLEMENT D'UNE SEULE DIMENSION : trigger EXACT de HQ (k=6 / thr_pct=0.5) et
  exit EXACT de HQ (stop 1.2% / tp 2.4% / 10 bars, calé A PRIORI sur la magnitude
  quotidienne, AUCUN sweep). On change UNIQUEMENT : on retire er_min/adx_min.
  variant_of = HQ (GOLD) / HR (ES) : prolongation d'idées KILLED, déflation
  GLOBALE comprise (10e/11e test de l'arc momentum*, z requis encore durci).

  GARDE-FOU CONFOND assumé d'avance : un PASS sur GOLD seul sur 2021-2026 (bull
  1800→4300) reste suspect de bêta long. Les défenses sont (a) le bootstrap PAR
  JOURS du harness (si les gains se concentrent en peu d'épisodes, l'IC explose),
  (b) le contrôle ES (HY), (c) l'équilibre L/S. Si malgré tout HX passe, la reco
  à Sam le DIRA explicitement : valider en PAPER vs buy-and-hold avant tout.

  Non-doublon : hypothesis_key = hash(family, params, exit, assets, timeframe).
  {momentum, k6/thr0.5, GOLD/ES, 1d} ∉ registry (les 1d existants sont tous
  momentum_REGIME, famille différente) → 2 clés NOUVELLES.
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
        "id": "HX_gold_momentum_uncond_1d",
        "hypothesis_text": "Le momentum INCONDITIONNEL au quotidien (k=6/thr=0.5, "
                           "SANS filtre de régime) dégage une espérance nette POSITIVE "
                           "sur GOLD 1d (exit stop1.2%/tp2.4%/10j), i.e. le résidu vu "
                           "en momentum_regime 1d (HQ +1.55% mais n=12) est du momentum "
                           "time-series daily généralisable, pas un artefact du filtre, "
                           "et il survit avec PUISSANCE (~1045 signaux, n_eff>>30).",
        "family": "momentum",
        "params": {"k": 6, "thr_pct": 0.5},
        "exit_rule": {"stop_pct": 1.2, "tp_pct": 2.4, "horizon_bars": 10},
        "assets": ["GOLD"], "timeframe": "1d",
        "variant_of": "HQ_gold_momentum_regime_1d_swing",
        "_lake": {"GOLD": "GC=F"},
    },
    {
        "id": "HY_es_momentum_uncond_1d",
        "hypothesis_text": "CONTRÔLE de HX sur ES (pas de bull-gold) : le momentum "
                           "INCONDITIONNEL quotidien (k=6/thr=0.5) dégage une espérance "
                           "nette POSITIVE sur US500↔ES=F 1d (exit stop1.2%/tp2.4%/10j). "
                           "Si HX passe et HY échoue → l'edge gold daily est de la BÊTA "
                           "passive (bull séculaire), pas du momentum généralisable.",
        "family": "momentum",
        "params": {"k": 6, "thr_pct": 0.5},
        "exit_rule": {"stop_pct": 1.2, "tp_pct": 2.4, "horizon_bars": 10},
        "assets": ["US500"], "timeframe": "1d",
        "variant_of": "HR_es_momentum_regime_1d_swing",
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
