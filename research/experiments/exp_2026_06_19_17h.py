#!/usr/bin/env python3
"""Experience PRIME ANALYST 2026-06-19 17h.

CONTEXTE : l'arc momentum-intraday LAKE-EXPRIMABLE a ete declare FERME au midday
(13h) — momentum_regime + momentum_breakout 1h KILLED bien-powered sur 3
instruments independants (GOLD beta / ES negatif / DOLLAR negatif bien-powered).
Le lake ne contient QUE du 1h et du 1d (pas de 15m), donc aucun NOUVEAU test de
momentum intraday dans les familles existantes ne serait autre chose qu'un re-knob
de l'arc mort. Plutot que de churner la deflation, je teste la SEULE famille
implementee JAMAIS soumise au juge, et dont les donnees existent dans le lake :
`cot_extreme` (positionnement COT, cot_5y.parquet).

POURQUOI c'est utile (et pas du remplissage) :
  - cot_extreme est une CONFLUENCE de mon perimetre (ANALYST_PROTOCOL §2 la liste
    explicitement : extremes COT). Avant de demander a Sam un token pour une
    famille COMPOSEE `momentum x COT-non-foule` (cf. spec du rapport), il faut
    savoir si le composant COT porte le MOINDRE signal net de couts sur l'or. Si
    le composant standalone est mort, la famille composee ne vaut pas un token.
  - Famille jamais testee => cle de registry NOUVELLE par construction. Aucun
    sign-flip (direction decidee par la regle contrarian symetrique). Aucun sweep
    de parametre : seuils canoniques 10/90, exit swing fixee a priori, declaree.

HYPOTHESE (UNE seule, slot leger) :
  Les EXTREMES de positionnement speculatif net COT sur l'OR (net_specs <=10e
  percentile glissant => foule SHORT extreme => LONG ; >=90e percentile => foule
  LONG extreme => SHORT, mode contrarian) degagent une esperance NETTE de couts
  positive en swing daily. Falsifie si exp_net <= 0 OU IC95 borne basse <= 0 OU
  t < z deflate.

ANTI-LOOKAHEAD COT : cot_pctile(ts) = rang-percentile du DERNIER rapport COT GOLD
  dont la date est STRICTEMENT anterieure a la bougie, parmi TOUS les rapports
  GOLD anterieurs (fenetre expansive, min 52 semaines avant activation). Aucune
  valeur future n'entre dans le percentile. COT = donnee CONTEXTE (ctx_fn), PAS
  une 2e serie de PRIX : la serie de prix reste mono-source (GC=F 1d).

Source HOMOGENE : GOLD <-> GC=F 1d (prix). COT GOLD en contexte.
"""

import json
import os
import sys

import pandas as pd

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "research"))
import harness
import datalake

_MIN_HISTORY = 52  # semaines de COT avant d'activer le percentile (anti-bruit)


def build_cot_ctx_fn(cot_asset="GOLD"):
    """Retourne ctx_fn(ts_epoch) -> {'cot_pctile': p} anti-lookahead."""
    df = pd.read_parquet(os.path.join(_ROOT, "research", "data", "cot_5y.parquet"))
    g = df[df["asset"] == cot_asset].copy()
    g["date"] = pd.to_datetime(g["date"])
    g = g.sort_values("date").reset_index(drop=True)
    dates = g["date"].values
    specs = g["net_specs"].astype(float).tolist()
    date_epochs = [pd.Timestamp(d).timestamp() for d in dates]

    def ctx_fn(ts_epoch):
        # index du dernier rapport STRICTEMENT anterieur a la bougie
        k = -1
        for idx, de in enumerate(date_epochs):
            if de < ts_epoch:
                k = idx
            else:
                break
        if k < _MIN_HISTORY:
            return None
        hist = specs[: k + 1]          # rapports connus a cette date (inclus le k-ieme)
        cur = hist[-1]
        # rang-percentile de la valeur courante parmi l'historique connu
        below = sum(1 for v in hist if v < cur)
        pct = 100.0 * below / (len(hist) - 1) if len(hist) > 1 else 50.0
        return {"cot_pctile": pct}

    return ctx_fn


STRATEGY = {
    "id": "IF_gold_cot_extreme_1d",
    "hypothesis_text": "Les EXTREMES de positionnement speculatif net COT sur l'OR "
                       "(net_specs <=10e pct glissant -> LONG ; >=90e pct -> SHORT, "
                       "mode contrarian) degagent une esperance NETTE de couts "
                       "positive en swing daily (exit stop2.5/tp4.0/horizon15). "
                       "Premiere soumission de la famille cot_extreme. Falsifie si "
                       "exp_net <= 0 OU IC95 borne basse <= 0 OU t < z deflate.",
    "family": "cot_extreme",
    "params": {"lo_pctile": 10, "hi_pctile": 90, "mode": "contrarian"},
    "exit_rule": {"stop_pct": 2.5, "tp_pct": 4.0, "horizon_bars": 15},
    "assets": ["GOLD"], "timeframe": "1d",
}


def main():
    ctx_fn = build_cot_ctx_fn("GOLD")
    candles, src = datalake.load_candles("GC=F", "1d")
    data = {"GOLD": candles}
    sources = {"GOLD": src}
    # diagnostic : combien de bougies declenchent un extreme ?
    fired = 0
    for c in candles:
        ctx = ctx_fn(float(c[0]))
        if ctx and (ctx["cot_pctile"] <= 10 or ctx["cot_pctile"] >= 90):
            fired += 1
    print(f"diagnostic: {fired}/{len(candles)} bougies en extreme COT (lo10/hi90)")

    r = harness.evaluate(STRATEGY, data, sources=sources, ctx_fn=ctx_fn)
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
