#!/usr/bin/env python3
"""TEST dérivation des 3 features order-flow (foundation A2, câblé 2026-06-18) +
threading compact R['orderflow'] -> décision. Pur : aucune base ouverte, aucun
réseau. Le payload threadé est COMPACT (poc/vah/val/recent_delta), pas le dict
analyze() complet, pour ne pas gonfler le .jsonl d'événements."""
import feature_store as fs
import prime_strategy as ps

FAIL = []


def chk(n, ok, d=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {n}" + (f", {d}" if d else ""))
    if not ok:
        FAIL.append(n)


print("Dérivation _orderflow_features (payload compact plat)")
of = {"poc": 100.0, "vah": 110.0, "val": 90.0, "recent_delta": 42.0}
de, imb, pocd = fs._orderflow_features(of, 105.0)
chk("of_delta = recent_delta", de == 42.0, str(de))
chk("of_poc_dist = (price-poc)/price", pocd == round((105.0 - 100.0) / 105.0, 5), str(pocd))
chk("of_imbalance = position Value Area (0.75)", imb == round((105.0 - 90.0) / (110.0 - 90.0), 4), str(imb))
_, imb_lo, _ = fs._orderflow_features(of, 80.0)
chk("price < VAL -> of_imbalance < 0", imb_lo < 0, str(imb_lo))
_, imb_hi, _ = fs._orderflow_features(of, 120.0)
chk("price > VAH -> of_imbalance > 1", imb_hi > 1, str(imb_hi))

print("Robustesse : données manquantes / dégénérées -> None propre")
chk("of absent -> (None, None, None)", fs._orderflow_features(None, 100.0) == (None, None, None))
chk("price absent -> (None, None, None)", fs._orderflow_features(of, None) == (None, None, None))
of_deg = {"poc": 100.0, "vah": 100.0, "val": 100.0}
dd, ii, pp = fs._orderflow_features(of_deg, 105.0)
chk("Value Area dégénérée (vah==val) -> of_imbalance None", ii is None)
chk("recent_delta absent -> of_delta None", dd is None)
chk("of_poc_dist calculé même si VA dégénérée", pp is not None, str(pp))

print("Compaction _of_compact : réduit le dict analyze() complet")
full = {"orderflow": {"poc": 100.0, "vah": 110.0, "val": 90.0, "vwap": 101.0,
                      "signals": ["a", "b", "c"], "hvn": [1, 2], "lvn": [3, 4],
                      "score": 0.7, "delta": {"recent_delta": 5.0, "cum_delta": 9.9}}}
comp = ps._of_compact(full)
chk("compact = poc/vah/val/recent_delta uniquement", set(comp.keys()) == {"poc", "vah", "val", "recent_delta"}, str(comp))
chk("compact ne contient PAS signals/hvn/lvn", "signals" not in comp and "hvn" not in comp)
chk("of vide -> compact None", ps._of_compact({"orderflow": {}}) is None)

print("Threading : la décision evaluate() porte le payload compact")
ps.news_radar.radar = lambda: {"fear_greed": {}, "gold_bias": 0, "spx_bias": 0, "items": []}
ps.news_radar._window_alert = lambda rad: ("🟢", "ok")
ps._adaptive_policy = lambda: {"mode": "TEST", "label": "s", "reason": "", "filters": {}}
ps.scanner.scan = lambda: {"setups": [], "regimes": {"GOLD": {}, "US500": {}}}
OF = {"poc": 100.0, "vah": 110.0, "val": 90.0, "delta": {"recent_delta": 5.0}}
ps._forecast_bias = lambda asset: (
    {"tf": {"15m": 0, "1h": 0, "4h": 0}, "price": 105.0, "price_source": "tradingview",
     "source_degraded": False, "orderflow": OF}, "NEUTRAL")
out = ps.evaluate()
g = [x for x in out["decisions"] if x["asset"] == "GOLD"][0]
chk("décision porte le compact (pas le dict complet)",
    g.get("orderflow") == {"poc": 100.0, "vah": 110.0, "val": 90.0, "recent_delta": 5.0}, str(g.get("orderflow")))
de2, imb2, pocd2 = fs._orderflow_features(g.get("orderflow"), g.get("price"))
chk("features dérivables depuis la décision réelle", de2 == 5.0 and pocd2 is not None and imb2 is not None,
    f"delta={de2} poc_dist={pocd2} imb={imb2}")

print()
if FAIL:
    print(f"X ÉCHEC(S): {FAIL}")
    raise SystemExit(1)
print("OK, dérivation + compaction + threading order-flow validés.")
