#!/usr/bin/env python3
"""Experience PRIME ANALYST 2026-06-19 13h (momentum INTRADAY + confluence).

ANGLE NEUF : un TROISIEME instrument pour TRANCHER le confond "beta-gold".

POURQUOI (et pas un re-knob ni un sign-flip) :
  - Depuis 3 sessions le verdict trend-following retombe sur la MEME signature :
    positif (non-significatif) sur GOLD, negatif/plat sur ES (HQ/HU, HZ/IA, IB/IC).
    Cross-read constant : la positivite n'existe QUE sur l'or -> beta passive du
    gold haussier, pas un edge de momentum generalisable. MAIS deux instruments ne
    suffisent pas a fermer la question : GOLD est confondu (bull-beta), ES est un
    seul controle.
  - Le DOLLAR (DX-Y.NYB) est l'arbitre ideal : instrument macro tres liquide qui
    TREND fort en intraday (data US, Fed) et qui n'est PAS une beta haussiere
    passive sur la periode (le DXY a ete rangebound/baissier). Si le momentum
    intraday est le vrai facteur UMD, il doit apparaitre AUSSI sur le dollar. S'il
    est plat/negatif sur DX comme sur ES -> la positivite gold = beta, point final,
    sur un 3e instrument independant et aux DEUX modes d'entree.

PAIRE (2 familles, 1 instrument neuf, INTRADAY 1h, AUCUN parametre retouche) :
  - ID = momentum_regime 1h sur DOLLAR -> SUBSTITUTION D'INSTRUMENT PURE de HH
    (gold 1h, KILLED) : MEMES params (k6/thr0.5/er0.45/adx30) et MEME exit
    (stop0.6/tp1.0/h24). On n'isole QUE l'instrument.
  - IE = momentum_breakout 1h sur DOLLAR -> SUBSTITUTION PURE de HS (gold 1h,
    KILLED) : MEMES params (lookback20/er0.45/adx30) et MEME exit. C'est l'entree-
    MARCHE sur cassure (la these capture §81b : suivre le momentum, pas le repli).

NON-DUPLICATE / NON-SIGN-FLIP / NON-SWEEP :
  - hypothesis_key = hash(family, params, exit, assets, tf) ; l'actif change
    -> cle NOUVELLE. variant_of declare (deflation comprise, compteur global).
  - AUCUNE valeur pechee : params/exit copies a l'identique de HH/HS. La seule
    variable manipulee est l'instrument -> test propre du confond.
  - Direction NON imposee : momentum/cassure decident LONG ou SHORT par
    construction symetrique. Aucun retournement de signe d'un resultat anterieur.

CAVEAT COUTS : DOLLAR n'est pas dans costs.COSTS -> couts FALLBACK_PCT generiques
  (spread session 2bps, slippage 1.5bps, swap 0.010%/nuit). DX-Y.NYB n'est pas un
  actif que le bot trade : c'est une SONDE de facteur, pas une reco de trading. Les
  couts generiques sont realistes pour un future DX tres liquide mais a lire comme
  une approximation.

Source HOMOGENE par test (DOLLAR <-> DX-Y.NYB), jamais melangee.
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
        "id": "ID_dollar_momentum_regime_1h",
        "hypothesis_text": "Le momentum conditionne au regime de tendance propre "
                           "(ER>=0.45 ET ADX>=30) en INTRADAY 1h degage une "
                           "esperance nette POSITIVE sur le DOLLAR (DX-Y.NYB), "
                           "memes params/exit que HH (gold 1h, KILLED). 3e "
                           "instrument independant pour trancher le confond "
                           "beta-gold. Falsifie si exp_net <= 0 ou IC95 borne "
                           "basse <= 0 ou t < z deflate.",
        "family": "momentum_regime",
        "params": {"k": 6, "thr_pct": 0.5, "er_min": 0.45, "adx_min": 30.0},
        "exit_rule": {"stop_pct": 0.6, "tp_pct": 1.0, "horizon_bars": 24},
        "assets": ["DOLLAR"], "timeframe": "1h",
        "variant_of": "HH_gold_momentum_regime_1h",
        "_lake": {"DOLLAR": "DX-Y.NYB"},
    },
    {
        "id": "IE_dollar_momentum_breakout_1h",
        "hypothesis_text": "Le momentum intraday DOLLAR 1h se capte par ENTREE-"
                           "MARCHE sur CASSURE du canal Donchian 20 bougies, "
                           "CONFIRMEE par regime tendanciel (ER>=0.45 ET ADX>=30), "
                           "exit stop0.6/tp1.0/24h, memes params/exit que HS "
                           "(gold 1h, KILLED). Substitution d'instrument pure : "
                           "l'edge cassure-momentum apparait-il sur un instrument "
                           "non-beta-gold ? Falsifie si exp_net <= 0 ou IC95 borne "
                           "basse <= 0 ou t < z deflate.",
        "family": "momentum_breakout",
        "params": {"lookback": 20, "er_min": 0.45, "adx_min": 30.0},
        "exit_rule": {"stop_pct": 0.6, "tp_pct": 1.0, "horizon_bars": 24},
        "assets": ["DOLLAR"], "timeframe": "1h",
        "variant_of": "HS_gold_momentum_breakout_1h",
        "_lake": {"DOLLAR": "DX-Y.NYB"},
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
