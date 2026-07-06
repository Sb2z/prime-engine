#!/usr/bin/env python3
"""Experience PRIME ANALYST du 2026-06-18 17h.

DEUX hypotheses NOUVELLES, falsifiables, motivees par un EVENEMENT LIVE du jour :
le bot a pousse a Sam a 13:45 Paris une alerte "MODE SCALP TENDANCE - GOLD SHORT"
(regime TENDANCE PROPRE, ADX15m 38.8, ER 0.491, 15m/1h alignes), fondee sur
"1 seul jour a 89% + stats agregees ADX>30 de 57 trades". C'est exactement le
filtre clean-trend (er0.45/adx30) deja TUE par HA (1d) et HH/HI (1h, exit HOLD
24 bars). MAIS la these SCALP differe de HH sur la dimension EXIT, jamais jugee :
HH = HOLD 24h (stop0.6/tp1.0/h24) ; le scalp = SORTIE RAPIDE, stop ATR serre.

POURQUOI ce test (et non du re-knob cosmetique) :
  - PRIORITE COURANTE du protocole (ANALYST_PROTOCOL section 81) : "RR / placement
    du TP optimal par regime" et "mode d'entree/sortie" sont LA dimension de
    recherche en cours. L'exit n'est pas un knob cosmetique : c'est le levier nomme.
  - DEVOIR : Sam recoit des alertes scalp en LIVE basees sur n=1 jour. L'analyste
    doit dire si cette these survit a l'histoire. Valider un signal deploye en
    direct par le juge n'est PAS du data-mining : c'est le coeur du lab.
  - NON-DOUBLON : hypothesis_key = hash(family, params, exit, assets, tf). HH/HI
    ont exit {stop0.6/tp1.0/h24}. Ici exit {stop0.5/tp0.7/h6} = cle NOUVELLE.
  - variant_of = HH (GOLD) / HI (ES) : prolongation d'idees KILLED, deflation
    GLOBALE comprise (z requis encore durci, c'est le cout assume).

EXIT calibre A PRIORI (AUCUN sweep) sur la magnitude d'une bougie GOLD 1h
(ATR ~0.4-0.5%) et la consigne LIVE "sortie rapide, stop ATR" :
  - horizon_bars=6 (6h max, vs 24h de HH) : scalp, pas hold.
  - stop_pct=0.5 (~1 ATR), tp_pct=0.7 : RR 1.4, profil scalp tendance.
Trigger et filtre IDENTIQUES a HH (k6/thr0.5/er0.45/adx30) : on ne change QUE
l'exit, pour isoler la question "la sortie rapide sauve-t-elle l'edge que le
hold 24h n'avait pas ?".

CONTROLE par PAIRE (comme HH<->HI) : HZ1=GOLD, HZ2=ES (pas de bull-gold).
Sources HOMOGENES separees (GOLD<->GC=F, US500<->ES=F, jamais melangees).
Lecture croisee :
  - HZ1 passe & HZ2 passe -> scalp clean-trend reel, non gold-specifique (rare).
  - HZ1 passe seul -> suspect beta-gold ; reco a Sam le DIRA (paper vs B&H).
  - les deux echouent -> la sortie rapide ne sauve pas le clean-trend : le filtre
    er0.45/adx30 reste mort meme en scalp -> resultat UTILE qui referme l'angle
    et conforte le caveat n=1 de l'alerte live.
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
        "id": "HZ1_gold_momentum_regime_1h_scalp",
        "hypothesis_text": "Le momentum clean-trend GOLD 1h (er>=0.45 & adx>=30, "
                           "trigger IDENTIQUE a HH) avec une SORTIE RAPIDE de scalp "
                           "(stop0.5/tp0.7/horizon 6 bars au lieu du HOLD 24h de HH) "
                           "degage une esperance nette POSITIVE, i.e. la sortie "
                           "rapide prescrite par l'alerte live 'MODE SCALP TENDANCE' "
                           "sauve l'edge que le hold 24h (HH, KILLED) n'avait pas.",
        "family": "momentum_regime",
        "params": {"k": 6, "thr_pct": 0.5, "er_min": 0.45, "adx_min": 30.0},
        "exit_rule": {"stop_pct": 0.5, "tp_pct": 0.7, "horizon_bars": 6},
        "assets": ["GOLD"], "timeframe": "1h",
        "variant_of": "HH_gold_momentum_regime_1h",
        "_lake": {"GOLD": "GC=F"},
    },
    {
        "id": "HZ2_es_momentum_regime_1h_scalp",
        "hypothesis_text": "CONTROLE de HZ1 sur ES (pas de bull-gold) : le momentum "
                           "clean-trend ES 1h (er>=0.45 & adx>=30) avec sortie rapide "
                           "de scalp (stop0.5/tp0.7/h6) degage une esperance nette "
                           "POSITIVE. Si HZ1 passe et HZ2 echoue -> l'edge scalp gold "
                           "est de la beta passive, pas du momentum generalisable.",
        "family": "momentum_regime",
        "params": {"k": 6, "thr_pct": 0.5, "er_min": 0.45, "adx_min": 30.0},
        "exit_rule": {"stop_pct": 0.5, "tp_pct": 0.7, "horizon_bars": 6},
        "assets": ["US500"], "timeframe": "1h",
        "variant_of": "HI_es_momentum_regime_1h",
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
            print(f"  fenetres: {[(w['n'], w['exp']) for w in r['per_window']]}")
            print(f"  checks: {r['checks']}")
        else:
            print(f"  {r.get('note')}")
    print(f"\nCompteurs lab: "
          f"{json.dumps(harness.lab_counters(), ensure_ascii=False)}")


if __name__ == "__main__":
    main()
