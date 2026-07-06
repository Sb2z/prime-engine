#!/usr/bin/env python3
"""Experience PRIME ANALYST 2026-06-19 09h (momentum intraday + confluences).

UN seul levier neuf, attaque par PAIRE (GOLD<->ES, comme HZ<->IA d'hier soir) :
la CASSURE DE NUAGE ICHIMOKU au SWING 1d -- confluence de tendance JAMAIS jugee
a cet horizon.

POURQUOI ce test (et pas du re-knob ni un sign-flip) :
  - TOUTE la batterie ichimoku du lab (HC kumo_break, HF tk_cross, HG kijun_reject,
    HJ chikou, HN/HO twist) a ete jugee sur 1h INTRADAY -> 6/6 KILLED. Le SWING 1d
    n'a JAMAIS recu de confluence ichimoku.
  - L'arc trend-following 1d a ete sonde par CASSURE DONCHIAN (HZ/IA hier, no-gate,
    bien-powered) et par momentum_regime (HQ/HR) -> KILLED, avec un cross-read clair :
    positivite GOLD seule = beta passive du gold haussier, ES infirme. La cassure de
    NUAGE est mecaniquement DISTINCTE d'une cassure de canal Donchian : le nuage
    melange la baseline 52p et la conversion, est deplace de 26 barres et s'epaissit
    avec la volatilite -> filtre de regime INTRINSEQUE. C'est la question canonique
    "l'entree Ichimoku de manuel paie-t-elle au swing sur les instruments de Sam ?".
  - DECISION-PERTINENT : meme grille de lecture bull-gold que HZ/IA. Si GOLD passe et
    ES echoue -> encore de la beta gold, pas un edge de confluence. Si les deux
    echouent -> la cassure de nuage 1d ne paie pas net de couts : referme l'angle
    "ichimoku au swing" avec des donnees.

NON-DUPLICATE / NON-SIGN-FLIP / NON-SWEEP :
  - hypothesis_key = hash(family, params, exit, assets, tf). HC = ichimoku_kumo_break
    sur 1h ; ici = MEME famille mais tf=1d + exit swing calibre + assets GOLD/ES
    separes -> cle NOUVELLE pour chaque actif. variant_of=HC_gold_kumo_break.
  - speed="standard" = le perimetre FERME approuve par Sam (9/26/52/26), AUCUN
    parametre libre balaye. Aucune valeur pechee.
  - Direction NON imposee : la cassure decide LONG (sort par le haut) ou SHORT (par
    le bas) par construction symetrique. Aucun sign-flip d'un resultat anterieur.

EXIT : l'UNIQUE exit 1d deja calibre du lab (stop1.2/tp2.4/horizon10, =HQ/HR/HV/HZ).
Aucun nouvel exit, aucun retuning -> on n'isole QUE la confluence de nuage au swing.

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
        "id": "IB_gold_ichimoku_kumo_1d",
        "hypothesis_text": "Une cloture 1d qui CASSE le nuage Ichimoku (speed "
                           "standard) sur GOLD continue dans le sens de la cassure "
                           "et degage une esperance nette POSITIVE net de couts a "
                           "l'horizon swing (exit calibre stop1.2/tp2.4/h10). "
                           "Falsifie si exp_net <= 0 ou IC95 borne basse <= 0 ou "
                           "t < z deflate.",
        "family": "ichimoku_kumo_break",
        "params": {"speed": "standard"},
        "exit_rule": {"stop_pct": 1.2, "tp_pct": 2.4, "horizon_bars": 10},
        "assets": ["GOLD"], "timeframe": "1d",
        "variant_of": "HC_gold_kumo_break",
        "_lake": {"GOLD": "GC=F"},
    },
    {
        "id": "IC_es_ichimoku_kumo_1d",
        "hypothesis_text": "CONTROLE de IB sur ES (pas de bull-gold) : la cassure "
                           "de nuage Ichimoku 1d (speed standard, memes exit/params "
                           "que IB) sur US500 degage une esperance nette POSITIVE. "
                           "Si IB passe et IC echoue -> l'edge cassure-nuage gold est "
                           "de la beta passive haussiere, pas une confluence "
                           "generalisable.",
        "family": "ichimoku_kumo_break",
        "params": {"speed": "standard"},
        "exit_rule": {"stop_pct": 1.2, "tp_pct": 2.4, "horizon_bars": 10},
        "assets": ["US500"], "timeframe": "1d",
        "variant_of": "IB_gold_ichimoku_kumo_1d",
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
