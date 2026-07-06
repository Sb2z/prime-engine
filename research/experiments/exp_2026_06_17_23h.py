#!/usr/bin/env python3
"""Expérience PRIME ANALYST du 2026-06-17 23h — slot EVENING (bilan séance, post-FOMC).

DEUX hypothèses NOUVELLES, falsifiables, données du lake (source homogène par
test : GOLD<->GC=F 1h, US500<->ES=F 1h ; aucune 2e source mélangée).

POURQUOI ce test — la famille `momentum_breakout` vient d'être APPROUVÉE par Sam
(token, commit 51a0e61 du 17/06) : c'était le backlog #1 explicite des 4 derniers
slots, "le seul angle « signal » intraday encore non réfuté". Spec analyste du
13/06. C'est le PREMIER test de cette famille au registry.

  Thèse de Sam, formulée proprement : le momentum intraday se capte par ENTRÉE-
  MARCHÉ SUR CASSURE (close franchit le plus-haut/plus-bas des `lookback` bougies
  ANTÉRIEURES) CONFIRMÉE par une tendance propre (ER>=0.45 ET ADX>=30) — l'OPPOSÉ
  d'OTE_RETRACEMENT (la prod, qui attend un repli et RATE les jours de tendance).
  Si le momentum intraday a un edge net de coûts quelque part dans les familles
  exprimables, c'est ICI qu'il doit apparaître : on suit la cassure au lieu de la
  fader. momentum_regime (ret>thr en régime) testait la PERSISTANCE ; le breakout
  teste le DÉCLENCHEMENT structurel (canal Donchian) — mécanisme distinct.

ISOLEMENT DES DEGRÉS DE LIBERTÉ — aucun sweep, paramètres tous hérités :
  - Gate de régime ER0.45/ADX30 = la porte CANONIQUE de toute la famille
    momentum_regime (HH..HR). Réutilisée TELLE QUELLE, pas re-tunée.
  - lookback=20 = canal Donchian classique (Turtle), valeur par défaut de la
    famille, choisie A PRIORI, pas balayée.
  - exit stop0.6/tp1.0/horizon24 = l'exit 1h CANONIQUE de HH (le momentum_regime
    1h GOLD) — réutilisé tel quel, calibré sur la vol horaire GOLD/ES. Aucun
    nouveau degré de liberté introduit ce soir.

PRÉ-EMPTION DU CONFOUND CROSS-ASSET (leçon HQ->HR) : un positif sur un SEUL actif
  est ininterprétable (cf. HQ GOLD 1d +1.55% qui n'était que le bull du gold,
  tranché par HR ES -0.40%). On teste donc DES LE DÉPART les DEUX actifs, config
  STRICTEMENT identique, seul l'actif change (H2 variant_of H1). Lecture :
    - Les DEUX passent (IC>0, t>=z, n_eff>=30) -> edge breakout cross-asset : le
      1er signal momentum intraday robuste du lab. Signal MAJEUR à Sam.
    - GOLD seul positif / ES plat ou négatif -> asset-spécifique, PAS un edge
      momentum généralisable (même verdict que HQ). Referme la piste breakout 1h.
    - Les DEUX plats/négatifs nets de coûts -> le momentum intraday ne se capte
      PAS plus par cassure que par persistance : la thèse intraday se referme sur
      les familles exprimables. Résultat utile (oriente vers nouvelles confluences).

Contexte d'ingestion (cf. rapport analyst_2026-06-17_23h.md) :
  - Santé bot VERTE : dernier cycle 22:56 Paris (frais <12 min), datafeed
    tradingview pur (6 flux), gate apprentissage 1450/500 (+126 depuis 17h),
    0 outcome MIXED, log propre, resim Gate-1 inchangé (USER WR 57.7% n=78
    exp -0.001%). Lab 25/24/0/0 (dont 4 fixtures TEST_JUDGE).
  - POST-FOMC : décision Fed tombée à 20:00 Paris. Bascule RISK-OFF nette :
    VIX +12.2%, DXY +0.85%, 10Y +1.04%. Forecast SHORT sur les DEUX actifs
    (GOLD repasse SHORT après être LONG l'aprem ; US500 SHORT confirmé). Régime
    TENDANCE HACHÉE 🔴 sur les deux. Cycles 20h->23h = NO_TRADE (session
    OVERNIGHT veto + RR<2). Bot correctement à l'écart en chop overnight.

Déflation : 9e/10e test de l'arc momentum* -> z requis encore durci (Bonferroni
  GLOBAL partagé avec le nocturne). Assumé : 1er test d'une famille NOUVELLE qui
  attaque le mécanisme d'entrée (cassure vs persistance), non cosmétique.

Non-doublon : hypothesis_key inclut family+params+asset+timeframe (harness.py) ;
  {momentum_breakout, GOLD/US500, 1h} est une famille jamais testée -> NOUVELLES.
"""

import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "research"))
import harness
import datalake


_COMMON = dict(
    family="momentum_breakout",
    params={"lookback": 20, "er_min": 0.45, "adx_min": 30.0},
    exit_rule={"stop_pct": 0.6, "tp_pct": 1.0, "horizon_bars": 24},
    timeframe="1h",
)

STRATEGIES = [
    {
        "id": "HS_gold_momentum_breakout_1h",
        "hypothesis_text": "Le momentum intraday GOLD 1h se capte par ENTRÉE-MARCHÉ "
                           "sur CASSURE du canal Donchian 20 bougies, CONFIRMÉE par "
                           "régime tendanciel (ER>=0.45 ET ADX>=30), exit "
                           "stop0.6/tp1.0/24h (canonique HH) : l'edge momentum, "
                           "absent en persistance (momentum_regime KILLED), "
                           "apparaît-il au DÉCLENCHEMENT structurel ?",
        "family": "momentum_breakout",
        "params": dict(_COMMON["params"]),
        "exit_rule": dict(_COMMON["exit_rule"]),
        "assets": ["GOLD"], "timeframe": "1h",
        "_lake": {"GOLD": "GC=F"},
    },
    {
        "id": "HT_us500_momentum_breakout_1h",
        "hypothesis_text": "Même breakout Donchian20 + gate ER0.45/ADX30 + exit "
                           "stop0.6/tp1.0/24h, sur US500 1h (ES=F) : SEUL l'actif "
                           "change vs HS. Si HS passe mais pas HT (ou inverse), "
                           "l'edge breakout est asset-spécifique (pas généralisable, "
                           "cf. confound HQ->HR). Si les deux passent, edge "
                           "momentum intraday cross-asset (1er du lab).",
        "family": "momentum_breakout",
        "params": dict(_COMMON["params"]),
        "exit_rule": dict(_COMMON["exit_rule"]),
        "assets": ["US500"], "timeframe": "1h",
        "variant_of": "HS_gold_momentum_breakout_1h",
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
