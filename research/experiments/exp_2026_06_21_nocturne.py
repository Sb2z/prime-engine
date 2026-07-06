#!/usr/bin/env python3
"""Experience CHERCHEUR NOCTURNE du 2026-06-21 (~23h30, run nocturne).

=== FERMETURE DE LA MATRICE ICHIMOKU AU SWING 1d (3 cellules vides comblees) ===

CONSTAT D'INGESTION : le lake yfinance est BYTE-IDENTIQUE a hier soir (dernier
bar GC=F/ES=F 1h = vendredi 19/06 03:00 UTC ; 1d = 19/06). Le download 07:00 a
tourne mais yfinance n'a rendu AUCUNE barre de week-end. La 1re surface intraday
neuve arrivera lundi 09h. => zero donnee neuve a l'horizon 1h.

CE QUI RESTE JUGEABLE sur cette surface : un audit signal-par-signal-par-horizon
du registry montre que la batterie ichimoku est fermee 5/5 a l'horizon 1h sur les
DEUX actifs tradables (GOLD: HC/HF/HG/HJ/HN ; US500: IC/IF/IG/IH/HO). Mais au
SWING 1d, SEUL kumo_break a ete juge (IB gold + IC es, 19/06). Les autres signaux
ichimoku n'ont JAMAIS recu de verdict a 1d :
  - ichimoku_tk_cross       (1h: HF gold +0.066% t=0.78 ; IF us500 -0.047% t=-0.45)
  - ichimoku_kijun_reject   (1h: HG gold -0.282% t=-5.97 ; IG us500 -0.038% t=-0.25)
  - ichimoku_chikou_confirm (1h: HJ gold -0.106% t=-2.57 ; IH us500 -0.020% t=+0.45)
Le nocturne 20/06 a EXPLICITEMENT teed-up ce move (backlog #1, route (b) : "1d
swing pour les 3 signaux non encore testes a cet horizon -- angle mineur, prior
tres faible"). twist_1d reste le SEUL residu (4e signal, hors budget 3/nuit ;
plus faible prior -- HN/HO twist a plat en 1h). Note dans le rapport, defere.

POURQUOI POOLER GOLD+US500 (et pas mono-actif comme IB/IC) :
  - L'horizon 1d est SOUS-PUISSANT en mono-actif : HQ (gold 1d) n_eff=12, HR (es 1d)
    n_eff=8 -> KILLED "faute de n", un close FAIBLE. Le remede de puissance nomme par
    le lab (17/06, HU/HV/HW) = POOLER les deux actifs cibles, source homogene yfinance
    (le harness concatene nativement les trades de `data`, la garde anti-basis
    n'interdit que les sources heterogenes). Pooler n'est ni un sweep ni un melange de
    sources : c'est EXACTEMENT le remede, in-lake. Un KILL poole bien-powered (n_eff>>30)
    est un close MESURE, pas une defaite de puissance.
  - Precedent exact : IB/IC = ichimoku generalise 1h->1d (mono) ; HU/HV/HW = pool
    GOLD+ES a 1d. Je combine les deux axes deja approuves. Aucun levier neuf.

ISOLEMENT DES DEGRES DE LIBERTE -- aucun parametre invente :
  - Trigger : speed="standard" = perimetre FERME 9/26/52/26 (= HF/HG/HJ/IB/IC...).
    Aucune valeur balayee, aucun knob.
  - Exit : l'UNIQUE exit 1d deja calibre du lab stop1.2/tp2.4/horizon10
    (= IB/IC/HQ/HR/HU/HV/HZ). Zero nouvel exit. On n'isole QUE l'horizon.
  - La SEULE chose neuve par hypothese = (assets pooled GOLD+US500) x (timeframe 1d)
    pour un signal dont le 1d n'a jamais ete juge. Tout le reste herite.

NON-DOUBLON / NON-SIGN-FLIP / NON-SWEEP :
  - hypothesis_key = hash(family, params, exit, sorted(assets), tf). assets=
    ["GOLD","US500"] poole + tf=1d != HF/HG/HJ (gold 1h mono) != IF/IG/IH (us500 1h
    mono) -> cle NOUVELLE pour chacune. variant_of declare (deflation Bonferroni
    comprise : chaque famille passe en test n°3).
  - Direction NON imposee : chaque signal decide LONG/SHORT par construction
    symetrique. Aucun retournement de signe d'un resultat anterieur.

VALEUR ATTENDUE (honnete) : prior TRES FAIBLE assume d'avance. 5/5 ichimoku morts
en 1h sur les 2 actifs ; kumo mort en 1d (IB/IC) ; cross-read recurrent du lab =
"positivite gold = beta passive du gold haussier, US500 infirme, rien ne paie net
de couts". J'ATTENDS 3 KILLED. La valeur n'est PAS de trouver un edge mais de
FERMER la matrice avec des donnees : apres cette nuit, ichimoku sera juge sur
{1h, 1d} x {GOLD, US500} pour 4/5 signaux (seul twist_1d residuel) -> "ichimoku
epuise au swing" cesse d'etre une assertion et devient un fait MESURE et bien-powered.
Si l'un PASSE (IC_bas>0, t>=z deflate, n_eff>=30, 2/3 fenetres +), c'est une
SURPRISE a revalider en PAPER (jamais promue ici), a prendre au serieux, pas a lisser.

Sources HOMOGENES (GOLD<->GC=F, US500<->ES=F, toutes deux yfinance ; jamais
melangees avec une autre source).

Contexte d'ingestion (re-verifie ce run) :
  - Pas de research/PAUSE.
  - resim Gate-1 USER inchange (WR 57.7% n=78 exp -0.001%, recent 8<15 decisifs).
  - feature_store gate 2378/500 (apprentissage_autorise=true, 0 MIXED, 291 setups).
  - Lake fige vendredi (0 bar neuf). Lab AVANT run : 41/40/0/0 (dont 4 fixtures).
  - Aucune injection externe (calendar/news traites en donnee seule).
"""

import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "research"))
import harness
import datalake

# Pool des deux actifs cibles, source homogene (yfinance), horizon swing 1d.
_POOL = {"GOLD": "GC=F", "US500": "ES=F"}
_EXIT_1D = {"stop_pct": 1.2, "tp_pct": 2.4, "horizon_bars": 10}  # = IB/IC/HQ/HR/HU

STRATEGIES = [
    {
        "id": "II_pool_ichimoku_tk_cross_1d",
        "hypothesis_text": "Le croisement Tenkan/Kijun confirme par la position vs "
                           "nuage (speed standard, exit swing stop1.2/tp2.4/h10) POOLE "
                           "GOLD+US500 a l'horizon 1d degage-t-il une esperance nette "
                           "POSITIVE ? Le tk_cross est plat en 1h (HF gold t=0.78, IF "
                           "us500 t=-0.45) ; le swing 1d, jamais juge, paie-t-il une "
                           "fois poole pour la puissance ? Falsifie si exp_net<=0 ou "
                           "IC95 borne basse<=0 ou t<z deflate.",
        "family": "ichimoku_tk_cross",
        "params": {"speed": "standard"},
        "exit_rule": dict(_EXIT_1D),
        "assets": ["GOLD", "US500"], "timeframe": "1d",
        "variant_of": "HF_gold_ichimoku_tk_cross",
        "_lake": dict(_POOL),
    },
    {
        "id": "IJ_pool_ichimoku_kijun_reject_1d",
        "hypothesis_text": "Le pullback rejete sur la Kijun, cloture du bon cote en "
                           "tendance de nuage (continuation-par-repli, speed standard, "
                           "exit swing stop1.2/tp2.4/h10) POOLE GOLD+US500 a 1d degage-t-il "
                           "une esperance nette POSITIVE ? Le 1h etait FRANCHEMENT negatif "
                           "sur gold (HG t=-5.97) mais bruit sur us500 (IG t=-0.25) ; le "
                           "swing 1d poole tranche-t-il ? Falsifie si exp_net<=0 ou IC95 "
                           "borne basse<=0 ou t<z deflate.",
        "family": "ichimoku_kijun_reject",
        "params": {"speed": "standard"},
        "exit_rule": dict(_EXIT_1D),
        "assets": ["GOLD", "US500"], "timeframe": "1d",
        "variant_of": "HG_gold_ichimoku_kijun_reject",
        "_lake": dict(_POOL),
    },
    {
        "id": "IK_pool_ichimoku_chikou_confirm_1d",
        "hypothesis_text": "La triple confluence Ichimoku (Chikou degagee + prix vs nuage "
                           "+ Tenkan>Kijun, speed standard, exit swing stop1.2/tp2.4/h10) "
                           "POOLEE GOLD+US500 a 1d degage-t-elle une esperance nette "
                           "POSITIVE ? Confluence la plus complete du manuel ichimoku ; "
                           "negative en 1h gold (HJ t=-2.57), bruit en 1h us500 (IH t=0.45) "
                           "; le swing 1d, jamais juge, paie-t-il ? Falsifie si exp_net<=0 "
                           "ou IC95 borne basse<=0 ou t<z deflate.",
        "family": "ichimoku_chikou_confirm",
        "params": {"speed": "standard"},
        "exit_rule": dict(_EXIT_1D),
        "assets": ["GOLD", "US500"], "timeframe": "1d",
        "variant_of": "HJ_gold_ichimoku_chikou_confirm",
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
            print(f"  fenetres: {[(w['n'], w['exp']) for w in r['per_window']]}")
            print(f"  checks: {r['checks']}")
        else:
            print(f"  {r.get('note')}")
    print(f"\nCompteurs lab: "
          f"{json.dumps(harness.lab_counters(), ensure_ascii=False)}")


if __name__ == "__main__":
    main()
