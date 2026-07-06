#!/usr/bin/env python3
"""Experience ANALYST 09h du 2026-06-22 (slot matinal, lundi — 1re surface NEUVE).

=== DERNIERE CELLULE DE LA MATRICE ICHIMOKU : twist_1d POOLE GOLD+US500 ===

CONSTAT D'INGESTION (re-verifie ce run, contrairement aux 4 derniers passages
du week-end ou le lake etait byte-identique) : le download 07:00 de ce lundi a
enfin rendu des barres NEUVES. Dernier bar GC=F/ES=F 1h = 2026-06-22 04:00 UTC
(vs vendredi 19/06 03:00 gele tout le week-end) ; 1d = 22/06. La "1re surface
intraday neuve = lundi 09h" promise par le nocturne 21/06 est arrivee. Le lake
a gagne ~1.5 jour (vendredi complet + lundi pre-marche).

POURQUOI CETTE HYPOTHESE, ET UNE SEULE :
  - Le nocturne 21/06 a ferme la matrice ichimoku 1d pour 4/5 signaux (kumo IB/IC ;
    tk_cross II ; kijun_reject IJ ; chikou_confirm IK), tous POOLES GOLD+US500,
    tous KILLED bien-powered (n_eff 36/69/249, exp≈0, IC chevauche 0). Le SEUL
    residu nomme et DEFERE etait twist_1d (4e signal, hors budget 3/nuit, prior
    le plus faible — HN/HO twist a plat en 1h). C'est la derniere cellule vide.
  - Les familles momentum (momentum, momentum_breakout, momentum_regime) sont
    KILLED sur {GOLD, ES, dollar, pool} x {1h, 1d}, exp≈0. Re-juger sur +1.5 jour
    de lake ne bougera pas un verdict poole bien-powered (et le registry dedoublonne).
    => 1 seule hypothese NEUVE et jugeable : twist_1d. Pas de churn pour cocher 2/2.

POURQUOI POOLER GOLD+US500 (remede de puissance nomme par le lab, 17/06 HU/HV/HW) :
  - Le swing 1d est SOUS-PUISSANT en mono-actif (HQ gold n=12, HR es n=8 -> KILLED
    "faute de n"). Pooler les deux actifs cibles en source homogene yfinance est
    le remede approuve (le harness concatene nativement, la garde anti-basis
    n'interdit que les sources heterogenes). Precedent exact : II/IJ/IK (nocturne
    21/06) = meme pool, meme horizon. Aucun levier neuf.
  - NOTE twist : le signal ne tire que sur twist_age==1 (changement de couleur du
    nuage FRAIS) + prix deja du bon cote. C'est un evenement RARE, surtout en 1d.
    Le pool peut malgre tout rester sous-puissant ; si KILLED "faute de n", c'est
    un fait mesure ("twist 1d trop rare meme poole"), pas une defaite a lisser.

ISOLEMENT DES DEGRES DE LIBERTE — aucun parametre invente :
  - Trigger : speed="standard" = perimetre FERME 9/26/52/26 (= tout le reste de
    la matrice ichimoku). Aucune valeur balayee, aucun knob.
  - Exit : l'UNIQUE exit 1d deja calibre du lab stop1.2/tp2.4/horizon10
    (= IB/IC/II/IJ/IK/HQ/HR/HU/HV/HZ). Zero nouvel exit.
  - SEULE chose neuve = (pool GOLD+US500) x (1d) x (signal twist) jamais juge a 1d.

NON-DOUBLON / NON-SIGN-FLIP : assets=["GOLD","US500"] poole + tf=1d + family
twist != HN (gold 1h mono) != HO (us500 1h mono) -> cle NOUVELLE. variant_of
declare (deflation Bonferroni comprise, test famille twist n°3). Direction NON
imposee : le signal decide LONG/SHORT par construction symetrique.

VALEUR ATTENDUE (honnete) : prior TRES FAIBLE. Twist plat en 1h (HN/HO) ;
4/5 ichimoku 1d deja morts exp≈0 ; cross-read recurrent du lab = "rien ne paie
net de couts au swing sur ce pool". J'ATTENDS 1 KILLED. La valeur n'est PAS de
trouver un edge mais de FERMER la matrice : apres ce run, ichimoku sera juge sur
{1h,1d} x {GOLD,US500} pour 5/5 signaux -> "ichimoku epuise au swing" devient un
fait MESURE complet, plus aucun residu. Si twist PASSE (IC_bas>0, t>=z deflate,
n_eff>=30, 2/3 fenetres +) c'est une SURPRISE a revalider en PAPER, jamais promue ici.

Sources HOMOGENES (GOLD<->GC=F, US500<->ES=F, toutes deux yfinance).

Contexte d'ingestion (re-verifie ce run) :
  - Pas de research/PAUSE.
  - resim Gate-1 USER inchange (WR 57.7% n=78 exp -0.001%, recent 8<15 decisifs).
  - feature_store gate 2486/500 (apprentissage_autorise=true, 0 MIXED, 299 setups,
    ret_4h se remplit 2648 non-null).
  - Lake NEUF (dernier bar lundi 22/06 04:00 UTC). Lab AVANT run : 44/43/0/0.
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

_POOL = {"GOLD": "GC=F", "US500": "ES=F"}
_EXIT_1D = {"stop_pct": 1.2, "tp_pct": 2.4, "horizon_bars": 10}  # = IB/IC/II/IJ/IK

STRATEGIES = [
    {
        "id": "IL_pool_ichimoku_twist_1d",
        "hypothesis_text": "Le twist du nuage (changement de couleur FRAIS, twist_age==1, "
                           "prix deja du bon cote ; speed standard, exit swing "
                           "stop1.2/tp2.4/h10) POOLE GOLD+US500 a l'horizon 1d degage-t-il "
                           "une esperance nette POSITIVE ? Dernier signal ichimoku jamais "
                           "juge a 1d ; plat en 1h (HN/HO) ; 4/5 ichimoku 1d deja morts "
                           "exp≈0. Falsifie si exp_net<=0 ou IC95 borne basse<=0 ou t<z "
                           "deflate ou n_eff insuffisant.",
        "family": "ichimoku_twist",
        "params": {"speed": "standard"},
        "exit_rule": dict(_EXIT_1D),
        "assets": ["GOLD", "US500"], "timeframe": "1d",
        "variant_of": "HN_gold_ichimoku_twist",
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
