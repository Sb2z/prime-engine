#!/usr/bin/env python3
"""Expériences du 13/06/2026, run nocturne n°4.

Trois hypothèses NOUVELLES, falsifiables, données du lake (source homogène
par test : prix yfinance ; le COT CFTC est un CONTEXTE fondamental via ctx_fn,
pas une 2e source de prix, la garde anti-basis du harness porte sur les prix).

Backlog d'hier honoré :
  • #1 (repoussé 2 runs) : CÂBLER cot_extreme via un ctx_fn cot_pctile SANS
    lookahead → HD (GOLD) et HE (US500). 1re mise à l'épreuve de la famille COT.
  • famille documentée jamais testée encore : Ichimoku TK-cross → HF (GOLD),
    1er test d'un mécanisme DIFFÉRENT du kumo_break tué le 12/06 (HC).

CHOIX DU TIMEFRAME COT = DAILY (1d), pas 1h. Le COT est un signal HEBDO :
le tester sur des bougies 1h fabrique des centaines de "trades" corrélés à
l'intérieur d'une même semaine d'extrême (le percentile est constant sur la
semaine). Sur 1d, un extrême ≈ 5 bougies, l'autocorrélation chute, et le lake
daily couvre 5 ans (260 rapports COT), échantillon propre pour un signal hebdo.

HD (cot_extreme, GOLD, 1d, 1er test famille → z 1.645) :
    "Quand le positionnement spéculatif net non-commercial sur l'or atteint un
     extrême (≤10e ou ≥90e percentile sur 156 semaines glissantes, COT connu
     avec lag de publication +4j), le prix MEAN-REVERTE, entrée contrarian."

HE (cot_extreme, US500/ES, 1d, 2e test famille → z 1.96, déflation Bonferroni) :
    "Le même extrême de positionnement COT mean-reverte aussi sur l'indice
     S&P 500." Robustesse cross-asset de la thèse HD (PAS un sign-flip : même
     direction contrarian, autre actif).

HF (ichimoku_tk_cross, GOLD, 1h, 1er test famille → z 1.645) :
    "Un croisement Tenkan/Kijun confirmé par la position du prix vs le nuage
     (LONG si croisement haussier ET close > nuage ; SHORT symétrique) entre
     en tendance et a une espérance nette positive sur l'or." Mécanisme
     CANONIQUE distinct de la cassure de nuage (HC, KILLED), pas une variante
     de sauvetage : l'un est un croisement de moyennes, l'autre une cassure de
     bord. Périmètre Ichimoku fermé, speed 'standard', aucun paramètre libre.

ANTI-LOOKAHEAD COT : le rapport CFTC daté du mardi T n'est publié que le
vendredi T+3. Le ctx_fn n'expose QUE les rapports dont (date + 4 jours) est
<= timestamp de la bougie de décision (bisect strict). Le percentile est
calculé sur les 156 derniers rapports CONNUS à cet instant ; comme le COT
remonte à 2021 et le lake daily à 2021 aussi, le warmup (≥52 rapports) est
satisfait dès les premières bougies de la fenêtre de test. Aucun paramètre
n'est retuné après résultat ; exits fixés A PRIORI.
"""

import bisect
import datetime as dt
import json
import sys

sys.path.insert(0, "/Users/sam/trading")
sys.path.insert(0, "/Users/sam/trading/research")
import harness
import datalake


def build_cot_ctx(asset, lookback=156, lag_days=4, min_hist=52):
    """ctx_fn(ts_epoch) -> {'cot_pctile': p} | None, SANS lookahead.

    p = rang-percentile (0-100) du net_specs le plus récent CONNU à ts parmi
    les `lookback` derniers rapports connus. 'Connu' = (date_rapport + lag_days)
    <= ts (lag de publication CFTC vendredi). None tant que < min_hist rapports.
    """
    df = datalake.load_cot()
    g = df[df.asset == asset].sort_values("date")
    avail = [(dt.datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc)
              + dt.timedelta(days=lag_days)).timestamp() for d in g["date"]]
    specs = [float(x) for x in g["net_specs"]]

    def ctx(ts_epoch):
        i = bisect.bisect_right(avail, ts_epoch)  # rapports strictement connus
        if i < 2:
            return None
        hist = specs[max(0, i - lookback):i]
        if len(hist) < min_hist:
            return None
        cur = hist[-1]
        return {"cot_pctile": 100.0 * sum(1 for x in hist if x <= cur) / len(hist)}
    return ctx


STRATEGIES = [
    {
        "id": "HD_gold_cot_extreme",
        "hypothesis_text": "Positionnement spéculatif COT extrême sur l'or "
                           "(<=10e/>=90e pctile/156s, lag pub +4j) -> "
                           "mean-reversion contrarian (daily).",
        "family": "cot_extreme",
        "params": {"lo_pctile": 10, "hi_pctile": 90, "mode": "contrarian"},
        "exit_rule": {"stop_pct": 2.5, "tp_pct": 2.5, "horizon_bars": 10},
        "assets": ["GOLD"], "timeframe": "1d",
        "_lake": {"GOLD": "GC=F"}, "_cot": "GOLD",
    },
    {
        "id": "HE_es_cot_extreme",
        "hypothesis_text": "Même extrême COT contrarian mean-reverte aussi sur "
                           "le S&P 500 (robustesse cross-asset de HD, daily).",
        "family": "cot_extreme",
        "params": {"lo_pctile": 10, "hi_pctile": 90, "mode": "contrarian"},
        "exit_rule": {"stop_pct": 1.8, "tp_pct": 1.8, "horizon_bars": 10},
        "assets": ["US500"], "timeframe": "1d",
        "_lake": {"US500": "ES=F"}, "_cot": "US500",
    },
    {
        "id": "HF_gold_ichimoku_tk_cross",
        "hypothesis_text": "Croisement Tenkan/Kijun confirmé par la position vs "
                           "nuage (canonique) entre en tendance sur l'or (1h).",
        "family": "ichimoku_tk_cross",
        "params": {"speed": "standard"},
        "exit_rule": {"stop_pct": 0.8, "tp_pct": 1.5, "horizon_bars": 48},
        "assets": ["GOLD"], "timeframe": "1h",
        "_lake": {"GOLD": "GC=F"}, "_cot": None,
    },
]


def main():
    for s in STRATEGIES:
        lake_map = s.pop("_lake")
        cot_asset = s.pop("_cot")
        data, sources = {}, {}
        for asset, ticker in lake_map.items():
            candles, src = datalake.load_candles(ticker, s["timeframe"])
            data[asset] = candles
            sources[asset] = src
        ctx_fn = build_cot_ctx(cot_asset) if cot_asset else None
        r = harness.evaluate(s, data, sources=sources, ctx_fn=ctx_fn)
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
