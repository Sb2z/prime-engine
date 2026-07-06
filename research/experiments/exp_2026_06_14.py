#!/usr/bin/env python3
"""Expériences du 14/06/2026, run nocturne n°5.

Trois hypothèses NOUVELLES, falsifiables, données du lake (source homogène
par test : prix yfinance ; aucune 2e source mélangée). Exits fixés A PRIORI,
aucun paramètre retuné après résultat.

Contexte d'ingestion (cf. rapport) : journal inchangé (dernier trade USER
08/06), 0 Prime / 0 PAPER → rien à autopsier côté exécution. feature_store
2430 features mais 72 outcomes (gate 72/500 figé). Macro sans surprise neuve
depuis le PPI chaud du 11/06. Or toujours en marché haussier structurel.

Choix des 3 hypothèses, motivés (pas un balayage de périmètre) :

HG (ichimoku_kijun_reject, GOLD, 1h, 1er test famille → z 1.645) :
    "Un pullback qui touche la Kijun et CLÔTURE du bon côté, en tendance de
     nuage (prix au-dessus du nuage → LONG ; symétrique SHORT), a une
     espérance nette positive sur l'or 1h." Backlog #3 du 13/06. Mécanisme de
     CONTINUATION-PAR-REPLI, structurellement DIFFÉRENT des deux cassures déjà
     réfutées (kumo_break HC, tk_cross HF) : ni une cassure de bord ni un
     croisement de moyennes, mais un rejet de support dynamique en tendance, précisément le setup qui DEVRAIT payer en marché directionnel si un
     signal Ichimoku paie. Périmètre Ichimoku fermé, speed 'standard'.

HH (momentum_regime, GOLD, 1h, variant_of=HA → z 1.960) :
    "Le momentum CONDITIONNÉ au régime de tendance propre (ER>=0.45 ET
     ADX>=30) a une espérance nette positive sur l'or en INTRADAY 1h."
    HA avait tué ce filtre en DAILY (exp ~0, le filtre réduit n sans déplacer
     l'espérance). MAIS Prime arme ses trend-days en INTRADAY, pas en daily :
     HA testait le bon mécanisme sur le MAUVAIS timeframe. HH teste la thèse
     trend-day de Prime sur son TF NATIF. Paramètres canoniques identiques à
     HA (ER 0.45 / ADX 30, k 6, thr 0.5), seul le TF change, ce qui ISOLE la
     question du timeframe (clé d'hypothèse distincte car tf=1h ≠ 1d).
     variant_of=HA_gold_momentum_regime, déflation comprise.

HI (momentum_regime, US500, 1h, variant_of=HA → z 2.128 après HH) :
    "Le même momentum conditionné au régime se généralise à l'indice S&P 500
     en 1h (robustesse cross-asset de HH)." Paire cross-asset exactement comme
     HD/HE l'ont fait pour le COT (précédent endossé). Mêmes paramètres
     canoniques, aucun tuning. La déflation Bonferroni durcit z à 2.128 (3e
     test à vie de la famille momentum_regime), assumé.

NON TESTÉ ce soir, et POURQUOI (backlog #1, COT conditionné au régime range) :
    On POURRAIT le composer sans toucher aux fichiers protégés (un ctx_fn qui
    n'expose cot_pctile QUE si l'ER calculé à ts est bas). Mais (a) il famine
    par construction : l'inconditionnel HD ne donnait déjà que n_eff=29 (<30) ;
    le filtrer par régime le passe SOUS le plancher → KILLED garanti par
    l'échantillon, pas par l'edge, zéro information nouvelle au-delà de la
    famine déjà établie le 13/06 ; et (b) un 3e enregistrement cot_extreme au
    registry DÉFLATERAIT À VIE la famille (z 2.13 → 2.34), durcissant le futur
    test COT MULTI-ACTIFS, le seul qui guérirait vraiment la famine. Le coût
    net est négatif. Donc : SPEC d'une famille cot_extreme_regime décrite dans
    le rapport pour approbation de Sam, et PAS de test cot_extreme ce soir.
    SIGN-FLIP toujours interdit : aucun "COT-follow" gratuit n'est dérivé du
    -0.46% de HD.
"""

import json
import sys

sys.path.insert(0, "/Users/sam/trading")
sys.path.insert(0, "/Users/sam/trading/research")
import harness
import datalake


STRATEGIES = [
    {
        "id": "HG_gold_ichimoku_kijun_reject",
        "hypothesis_text": "Pullback rejeté sur la Kijun, clôture du bon côté en "
                           "tendance de nuage (continuation-par-repli) -> "
                           "espérance nette positive sur l'or 1h.",
        "family": "ichimoku_kijun_reject",
        "params": {"speed": "standard"},
        "exit_rule": {"stop_pct": 0.8, "tp_pct": 1.5, "horizon_bars": 48},
        "assets": ["GOLD"], "timeframe": "1h",
        "variant_of": None,
        "_lake": {"GOLD": "GC=F"},
    },
    {
        "id": "HH_gold_momentum_regime_1h",
        "hypothesis_text": "Momentum conditionné au régime de tendance (ER>=0.45 "
                           "ET ADX>=30) en INTRADAY 1h sur l'or, thèse trend-day "
                           "de Prime sur son TF natif (HA l'avait testée en daily).",
        "family": "momentum_regime",
        "params": {"k": 6, "thr_pct": 0.5, "er_min": 0.45, "adx_min": 30.0},
        "exit_rule": {"stop_pct": 0.6, "tp_pct": 1.0, "horizon_bars": 24},
        "assets": ["GOLD"], "timeframe": "1h",
        "variant_of": "HA_gold_momentum_regime",
        "_lake": {"GOLD": "GC=F"},
    },
    {
        "id": "HI_es_momentum_regime_1h",
        "hypothesis_text": "Le momentum conditionné au régime se généralise à "
                           "l'indice S&P 500 en 1h (robustesse cross-asset de HH).",
        "family": "momentum_regime",
        "params": {"k": 6, "thr_pct": 0.5, "er_min": 0.45, "adx_min": 30.0},
        "exit_rule": {"stop_pct": 0.6, "tp_pct": 1.0, "horizon_bars": 24},
        "assets": ["US500"], "timeframe": "1h",
        "variant_of": "HA_gold_momentum_regime",
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
