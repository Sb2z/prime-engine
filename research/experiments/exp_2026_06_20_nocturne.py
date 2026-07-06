#!/usr/bin/env python3
"""Experience CHERCHEUR NOCTURNE du 2026-06-20 (~23h45).

=== FERMETURE DE LA MATRICE ICHIMOKU x US500 (3 cellules vides comblees) ===

Constat en ouvrant le registry asset-par-asset (et non famille-par-famille) :
la batterie ichimoku a ete jugee A FOND sur GOLD (HC kumo, HF tk_cross, HG
kijun_reject, HJ chikou, HN twist -> 5/5 KILLED) mais seulement DEUX des cinq
signaux ont ete generalises a US500 : kumo (IC, 1d) et twist (HO, 1h). Restent
TROIS cellules JAMAIS jugees sur l'instrument US500 a l'horizon 1h intraday :
  - ichimoku_tk_cross      (GOLD = HF, KILLED, n=161, exp +0.066%, t=0.78)
  - ichimoku_kijun_reject  (GOLD = HG, KILLED, n=395, exp -0.282%, t=-5.97)
  - ichimoku_chikou_confirm(GOLD = HJ, KILLED, n=614, exp -0.106%, t=-2.57)

POURQUOI ce test (et pas du re-knob, ni un sign-flip, ni du churning) :
  - US500 est un actif TRADE par le bot (on-theme) ; ES=F est dans le lake
    (13719 barres 1h, source yfinance homogene) -> jugeable cette nuit.
  - C'est la MEME question de validite externe que HO (twist US500), qui est le
    PRECEDENT exact : meme famille, MEMES params (speed=standard, perimetre FERME
    9/26/52/26), MEME exit canonique ichimoku-1h (stop0.8/tp1.5/h48 = HF/HG/HJ/HO),
    asset change GOLD->US500. Aucun parametre balaye, aucune valeur pechee.
  - Direction NON imposee : chaque signal decide LONG/SHORT par construction
    symetrique. Aucun retournement de signe d'un resultat anterieur.
  - hypothesis_key = hash(family, params, exit, assets, tf) ; assets=US500 (vs
    GOLD pour HF/HG/HJ) -> cle NOUVELLE pour chacun. variant_of declare ->
    deflation Bonferroni comprise : chaque famille passe en test n°2 (z 1.96).

VALEUR ATTENDUE (honnete) : prior FAIBLE. 5/5 ichimoku morts sur GOLD ; kumo+twist
morts sur US500 aussi ; le cross-read recurrent du lab = "positivite GOLD = beta
passive du gold haussier, US500 infirme, rien ne paie net de couts". J'ATTENDS
3 KILLED. La valeur n'est PAS de trouver un edge mais de FERMER la matrice avec
des donnees : apres cette nuit, ichimoku sera juge EXHAUSTIVEMENT sur les DEUX
actifs tradables -> le constat "ichimoku epuise" cesse d'etre une assertion avec
3 cellules vides et devient un fait demontre. Si l'un passe, c'est un signal a
revalider en PAPER (jamais promu ici) — surprise a prendre au serieux, pas a lisser.

Sources HOMOGENES (US500 <-> ES=F, jamais melangees).
"""

import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "research"))
import harness
import datalake


_ICHI_EXIT = {"stop_pct": 0.8, "tp_pct": 1.5, "horizon_bars": 48}  # = HF/HG/HJ/HO

STRATEGIES = [
    {
        "id": "IF_us500_ichimoku_tk_cross_1h",
        "hypothesis_text": "Validite externe de HF sur US500 (ES=F, 1h) : le "
                           "croisement Tenkan/Kijun confirme par la position vs "
                           "nuage (speed standard, memes exit/params que HF) degage "
                           "une esperance nette POSITIVE. Falsifie si exp_net<=0 ou "
                           "IC95 borne basse<=0 ou t<z deflate. Si HF(GOLD) et ce "
                           "test echouent -> tk_cross ne paie pas net de couts sur "
                           "les 2 actifs tradables.",
        "family": "ichimoku_tk_cross",
        "params": {"speed": "standard"},
        "exit_rule": dict(_ICHI_EXIT),
        "assets": ["US500"], "timeframe": "1h",
        "variant_of": "HF_gold_ichimoku_tk_cross",
        "_lake": {"US500": "ES=F"},
    },
    {
        "id": "IG_us500_ichimoku_kijun_reject_1h",
        "hypothesis_text": "Validite externe de HG sur US500 (ES=F, 1h) : le "
                           "pullback rejete sur la Kijun, cloture du bon cote en "
                           "tendance de nuage (continuation-par-repli, memes "
                           "exit/params que HG) degage une esperance nette POSITIVE. "
                           "Si HG(GOLD, t=-5.97) et ce test echouent -> kijun_reject "
                           "est refute sur les 2 actifs tradables.",
        "family": "ichimoku_kijun_reject",
        "params": {"speed": "standard"},
        "exit_rule": dict(_ICHI_EXIT),
        "assets": ["US500"], "timeframe": "1h",
        "variant_of": "HG_gold_ichimoku_kijun_reject",
        "_lake": {"US500": "ES=F"},
    },
    {
        "id": "IH_us500_ichimoku_chikou_confirm_1h",
        "hypothesis_text": "Validite externe de HJ sur US500 (ES=F, 1h) : la triple "
                           "confluence Ichimoku (Chikou degagee + prix vs nuage + "
                           "Tenkan>Kijun, memes exit/params que HJ) degage une "
                           "esperance nette POSITIVE. Si HJ(GOLD) et ce test "
                           "echouent -> la confluence ichimoku est refutee sur les "
                           "2 actifs tradables a l'horizon 1h.",
        "family": "ichimoku_chikou_confirm",
        "params": {"speed": "standard"},
        "exit_rule": dict(_ICHI_EXIT),
        "assets": ["US500"], "timeframe": "1h",
        "variant_of": "HJ_gold_ichimoku_chikou_confirm",
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
