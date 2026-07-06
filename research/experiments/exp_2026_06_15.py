#!/usr/bin/env python3
"""Expériences du 15/06/2026 — run nocturne n°6.

Deux hypothèses NOUVELLES, falsifiables, données du lake (source homogène par
test : prix yfinance ; aucune 2e source mélangée). Exits fixés A PRIORI selon
les conventions héritées (aucun paramètre retuné après résultat).

Contexte d'ingestion (cf. rapport) :
  - journal.json INCHANGÉ (dernier trade USER 08/06 13:00, 0 trade neuf, 0
    signal Prime, 0 PAPER actif) → rien à autopsier côté exécution.
  - resim USER inchangé : WR 57.7 % n=78 exp -0.001 % ; fenêtre récente n=8
    décisifs (< 15, insuffisant), forward-test en cours.
  - feature_store : **2942 features / 489 outcomes complets** → gate
    **489/500** (apprentissage_autorise=false MAIS à ~11 outcomes du seuil ;
    saut majeur depuis 72/500 figé sur 4 runs — les outcomes se bouclent enfin).
  - Mining trades réels TENTÉ : métadonnées dégénérées (session="REAL" partout,
    score=None, adx<30 uniforme) → non minables ; backlog #5 (attendre n≈150)
    confirmé. Sam trade GOLD à 66/78, d'où le choix de l'actif pour HK.
  - Macro : 12→15/06 sans surprise RÉALISÉE à miner (actuals nuls) ; gros bloc
    banques centrales À VENIR (BoJ/RBA 16/06, FOMC 17/06) — rien d'exploitable
    en dérive post-event tant que les surprises ne sont pas publiées.
  - Lake frais : GC=F/ES=F 1h = 13 732 / 13 694 barres (→ 2026-06-15).

Choix des 2 hypothèses (PAS un balayage ; nuit volontairement resserrée) :

HJ (ichimoku_chikou_confirm, GOLD, 1h, 1er test famille → z 1.645) :
    "La configuration Ichimoku de TRIPLE confluence (Chikou dégagée au-dessus
     du prix de t-disp, prix au-dessus du nuage, Tenkan > Kijun ; symétrique
     SHORT) a une espérance nette positive sur l'or 1h."
    Backlog #2 honoré avec RAISON SPÉCIFIQUE : les 3 mécanismes Ichimoku déjà
    réfutés (kumo_break HC, tk_cross HF, kijun_reject HG) sont tous des entrées
    à TRIGGER UNIQUE. chikou_confirm est structurellement différent : un FILTRE
    de CONFLUENCE qui exige l'alignement de trois composantes indépendantes —
    le setup "haute conviction" canonique d'Ichimoku. Si même la confluence la
    plus stricte ne paie pas net de coûts, on pourra déclarer Ichimoku quasi
    clos sur l'or 1h (resterait twist, backlog). Une seule famille Ichimoku ce
    soir (limite backlog respectée). Exit a priori = convention continuation
    héritée de HF/HG (stop 0.8 / tp 1.5 / 48 barres), AUCUN tuning.

HK (mean_reversion, GOLD, 1h, variant_of=H2 → z 1.960) :
    "Un excès intraday de ±1 % sur 6 bougies 1h sur l'OR mean-reverte (fade de
     l'excès)." H2 avait testé exactement ce mécanisme sur l'ES (US500) et l'a
     tué. HK est sa robustesse CROSS-ASSET sur l'OR — l'actif que Sam trade
     réellement (66/78 trades) et donc le plus pertinent à interroger. Mêmes
     paramètres canoniques que H2 (k 6, thr 1.0 ; exit 0.5/0.8/16) : seul
     l'actif change, ce qui ISOLE la question cross-asset (clé d'hypothèse
     distincte car assets=[GOLD] ≠ [US500]). variant_of=H2_es_meanrev_1pct,
     déflation Bonferroni comprise (2e test famille → z 1.96). Pas de famine :
     l'or 1h sur 2 ans génère largement assez d'excès ±1 %. AUCUN tuning.

NON TESTÉ ce soir, et POURQUOI :
  - 2e/3e mécanisme Ichimoku (twist) : limite backlog "au plus 1 Ichimoku/nuit".
    twist reste au backlog (mécanisme distinct : changement de couleur du nuage).
  - COT conditionné régime : famine garantie (n<30) + déflation à vie de la
    famille tant que le lake COT reste GOLD+US500 → SPEC à Sam, pas de test
    (inchangé depuis le 14/06). SIGN-FLIP toujours interdit (aucun COT-follow
    gratuit dérivé du -0.46 % de HD ; aucun "fade des pullbacks" dérivé de HG).
  - Re-test momentum_regime : la famille a déjà 3 entrées à vie (HA/HH/HI), un
    4e test déflaterait à z~2.24 pour un edge mesuré ~0 — retuner ses seuils
    serait un sweep. Écarté.
"""

import json
import sys

sys.path.insert(0, "/Users/sam/trading")
sys.path.insert(0, "/Users/sam/trading/research")
import harness
import datalake


STRATEGIES = [
    {
        "id": "HJ_gold_ichimoku_chikou_confirm",
        "hypothesis_text": "Triple confluence Ichimoku (Chikou dégagée + prix vs "
                           "nuage + Tenkan>Kijun) -> espérance nette positive sur "
                           "l'or 1h. Filtre de confluence, distinct des 3 triggers "
                           "uniques déjà réfutés (kumo_break, tk_cross, kijun_reject).",
        "family": "ichimoku_chikou_confirm",
        "params": {"speed": "standard"},
        "exit_rule": {"stop_pct": 0.8, "tp_pct": 1.5, "horizon_bars": 48},
        "assets": ["GOLD"], "timeframe": "1h",
        "variant_of": None,
        "_lake": {"GOLD": "GC=F"},
    },
    {
        "id": "HK_gold_meanrev_1pct",
        "hypothesis_text": "Un excès de ±1% sur 6 bougies 1h sur l'OR mean-reverte "
                           "(fade de l'excès) — robustesse cross-asset de H2 (tué "
                           "sur l'ES) sur l'actif que Sam trade réellement.",
        "family": "mean_reversion",
        "params": {"k": 6, "thr_pct": 1.0},
        "exit_rule": {"stop_pct": 0.5, "tp_pct": 0.8, "horizon_bars": 16},
        "assets": ["GOLD"], "timeframe": "1h",
        "variant_of": "H2_es_meanrev_1pct",
        "_lake": {"GOLD": "GC=F"},
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
