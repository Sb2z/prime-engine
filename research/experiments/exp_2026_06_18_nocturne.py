#!/usr/bin/env python3
"""Experience CHERCHEUR NOCTURNE du 2026-06-18 (23h30).

UN seul levier neuf, attaque par PAIRE (GOLD<->ES, comme HS<->HT) :
la CASSURE DONCHIAN PURE (trend-following canonique, sans filtre de regime).

POURQUOI ce test (et pas du re-knob ni un sweep) :
  - L'arc breakout teste a ce jour a TOUJOURS impose le gate de regime propre
    (er>=0.45 ET adx>=30) : HS/HT (1h) et HV (1d poole). Ce gate quotidien est
    si selectif que la cassure ne s'arme presque jamais -> HV n_eff=14, une
    fenetre a 0 trade : le verdict KILLED de HV mesure surtout un MANQUE DE
    PUISSANCE, pas une absence d'edge de la cassure elle-meme.
  - La question CANONIQUE, jamais jugee proprement : le trend-following le plus
    classique qui existe -- la cassure de canal Donchian-20 SANS filtre de regime
    (= Turtle System 1, le defaut de manuel) -- degage-t-il une esperance nette
    positive sur les DEUX instruments que Sam trade, a l'horizon swing 1d ?
  - C'est DECISION-PERTINENT pour Sam : "faut-il juste lancer un breakout naif
    sur GOLD/US500 ?" est une question reelle et ouverte. Un verdict BIEN POWERED
    (la cassure no-gate s'arme souvent, contrairement a la version gated n=14)
    la referme avec des donnees, dans un sens ou dans l'autre.

NON-DUPLICATE / NON-SIGN-FLIP / NON-SWEEP :
  - hypothesis_key = hash(family, params, exit, assets, tf). er_min=0/adx_min=0
    (gate desactive) != er_min0.45/adx_min30 de HS/HT/HV -> cle NOUVELLE.
  - Mecaniquement DISTINCT de HX/HY (momentum incond 1d) : HX/HY = seuil sur le
    rendement k-barres ; ici = franchissement d'un EXTREME de canal (nouveau
    plus-haut/-bas 20j). Correle mais pas identique (la cassure ne s'arme QUE
    sur un nouvel extreme). Famille distincte (_momentum_breakout).
  - er_min=0/adx_min=0 n'est PAS un knob tune : c'est la BORNE DE PRINCIPE
    "aucun filtre" = la cassure Donchian pure de manuel. lookback=20 = le
    Donchian-20 canonique (pas une valeur pechee). Aucun parametre balaye.
  - Direction NON imposee : la cassure decide LONG (plus-haut) ou SHORT (plus-bas)
    par construction symetrique. Aucun sign-flip d'un resultat anterieur.

EXIT : l'UNIQUE exit 1d deja calibre du lab (stop1.2/tp2.4/horizon10, =HQ/HR/HV).
Aucun nouvel exit, aucun retuning -> on n'isole QUE la suppression du gate.

CONTROLE par PAIRE (bull-gold) :
  - GOLD passe & ES passe -> trend-following de cassure reel, non gold-specifique.
  - GOLD passe seul -> suspect beta passive du gold haussier (cf. HU : ~moitie du
    +1.55% de HQ etait le drift du seul gold) ; la reco a Sam le dira.
  - les deux echouent -> la cassure naive ne paie pas net de couts sur les
    instruments de Sam : resultat UTILE qui referme la question "turtles naifs".

Sources HOMOGENES separees (GOLD<->GC=F, US500<->ES=F, jamais melangees).
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
        "id": "HZ_gold_donchian_nogate_1d",
        "hypothesis_text": "La cassure Donchian-20 PURE (sans filtre de regime, "
                           "er_min=0/adx_min=0) sur GOLD 1d -- le trend-following "
                           "canonique de manuel (Turtle System 1) -- degage une "
                           "esperance nette POSITIVE net de couts a l'horizon swing "
                           "(exit 1d calibre stop1.2/tp2.4/h10). Falsifie si exp_net "
                           "<= 0 ou IC95 borne basse <= 0 ou t < z deflate.",
        "family": "momentum_breakout",
        "params": {"lookback": 20, "er_min": 0.0, "adx_min": 0.0},
        "exit_rule": {"stop_pct": 1.2, "tp_pct": 2.4, "horizon_bars": 10},
        "assets": ["GOLD"], "timeframe": "1d",
        "variant_of": "HV_pool_momentum_breakout_1d",
        "_lake": {"GOLD": "GC=F"},
    },
    {
        "id": "IA_es_donchian_nogate_1d",
        "hypothesis_text": "CONTROLE de HZ sur ES (pas de bull-gold) : la cassure "
                           "Donchian-20 PURE (er_min=0/adx_min=0) sur US500 1d degage "
                           "une esperance nette POSITIVE (memes exit/params que HZ). "
                           "Si HZ passe et IA echoue -> l'edge cassure gold est de la "
                           "beta passive haussiere, pas du trend-following generalisable.",
        "family": "momentum_breakout",
        "params": {"lookback": 20, "er_min": 0.0, "adx_min": 0.0},
        "exit_rule": {"stop_pct": 1.2, "tp_pct": 2.4, "horizon_bars": 10},
        "assets": ["US500"], "timeframe": "1d",
        "variant_of": "HZ_gold_donchian_nogate_1d",
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
