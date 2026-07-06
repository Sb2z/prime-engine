#!/usr/bin/env python3
"""TEST du protocole (lot 2026-06-18) :
  P4, plus de plancher RR FIXE ; garde-fou artefact sur RR trop haut.
  P4b, GARDE-FOU D'ESPÉRANCE au grade A (décision Sam 06-18) : espérance
        historique >= 0 si échantillon suffisant, sinon prior RR>=RR_A_PRIOR ;
        plancher de santé RR_A_MIN dans tous les cas.
  P4c, frontières inclusives des bornes RR.
  P1, source dégradée -> NO_TRADE d'office, price_source propagé.
  P1b, branche « aucun setup » (non dégradée) propage aussi price_source.
  Edge, A_SETUP rétrogradé en WATCH par une politique edge ACTIVE non conforme.
Isolé : scanner/news_radar/adaptive_edge/position_policy stubbés, aucun appel
réseau, aucun effet sur le live."""
import prime_strategy as ps

FAIL = []


def chk(n, ok, d=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {n}" + (f", {d}" if d else ""))
    if not ok:
        FAIL.append(n)


fc = {"tf": {"15m": 0.2, "1h": 0.2, "4h": 0.2}}

print("P4, plus de RR fixe : un setup haute-proba à RR modeste n'est plus tué")
s_lowrr = {"direction": "LONG", "rr": 1.5, "conf": 8.0}
v = ps._major_veto("GOLD", s_lowrr, fc, "🟢")
chk("RR 1.5 n'est plus un veto", not any("RR" in r for r in v), str(v))
chk("RR 1.5 + conf 8 + TF alignés -> A_SETUP", ps._grade(s_lowrr, [], fc) == "A_SETUP")

print("P4, garde-fou artefact : RR aberrant (stop microscopique) rejeté")
s_hi = {"direction": "LONG", "rr": 12.0, "conf": 8.0}
v2 = ps._major_veto("GOLD", s_hi, fc, "🟢")
chk("RR 12 vetoé (artefact)", any("RR" in r and "artefact" in r for r in v2), str(v2))
chk("RR 12 -> NO_TRADE", ps._grade(s_hi, v2, fc) == "NO_TRADE")

print("P4b, garde-fou d'espérance au grade A (remplace le RR fixe)")
_orig_stats = ps._stats_for
# Cold start : pas d'historique fiable -> prior RR_A_PRIOR (=1.5)
ps._stats_for = lambda strategy=None, trader=None, direction=None: {"n": 0, "expectancy": None}
chk("cold start RR 1.3 (<prior 1.5) -> WATCH",
    ps._grade({"direction": "LONG", "rr": 1.3, "conf": 8.0, "strategy": "X"}, [], fc) == "WATCH")
chk("cold start RR 1.5 (>=prior) -> A_SETUP",
    ps._grade({"direction": "LONG", "rr": 1.5, "conf": 8.0, "strategy": "X"}, [], fc) == "A_SETUP")
chk("plancher santé : RR 1.19 (<RR_A_MIN) -> WATCH",
    ps._grade({"direction": "LONG", "rr": 1.19, "conf": 8.0, "strategy": "X"}, [], fc) == "WATCH")
# Stratégie historiquement PERDANTE (n>=10, exp<0) : refusée même à bon RR
ps._stats_for = lambda strategy=None, trader=None, direction=None: {"n": 20, "expectancy": -0.3}
chk("strat perdante (exp<0, n>=10) RR 2.0 -> WATCH (le but c'est le profit)",
    ps._grade({"direction": "LONG", "rr": 2.0, "conf": 8.0, "strategy": "LOSER"}, [], fc) == "WATCH")
# Stratégie historiquement GAGNANTE (n>=10, exp>=0) : A_SETUP même à RR modeste
ps._stats_for = lambda strategy=None, trader=None, direction=None: {"n": 20, "expectancy": 0.4}
chk("strat gagnante (exp>=0) RR 1.3 -> A_SETUP",
    ps._grade({"direction": "LONG", "rr": 1.3, "conf": 8.0, "strategy": "WINNER"}, [], fc) == "A_SETUP")
ps._stats_for = _orig_stats

print("P4c, frontières inclusives des bornes RR")
chk("RR exactement 8.0 n'est PAS un veto artefact (borne stricte `>`)",
    not any("RR" in r for r in ps._major_veto("GOLD", {"direction": "LONG", "rr": 8.0, "conf": 8.0}, fc, "🟢")))
chk("RR 8.01 -> veto artefact",
    any("artefact" in r for r in ps._major_veto("GOLD", {"direction": "LONG", "rr": 8.01, "conf": 8.0}, fc, "🟢")))


def _stub_market():
    ps.news_radar.radar = lambda: {"fear_greed": {}, "gold_bias": 0, "spx_bias": 0, "items": []}
    ps.news_radar._window_alert = lambda rad: ("🟢", "ok")
    ps._adaptive_policy = lambda: {"mode": "TEST", "label": "stub", "reason": "", "filters": {}}


print("P1, source dégradée -> NO_TRADE d'office + price_source propagé")
_stub_market()
ps.scanner.scan = lambda: {
    "setups": [{"asset": "GOLD", "direction": "LONG", "conf": 8.0, "rr": 2.0,
                "entry": 3000, "stop": 2990, "tp": 3020, "regime": "TREND"}],
    "regimes": {"GOLD": {"regime": "TREND"}, "US500": {"regime": "TREND"}},
}
ps._forecast_bias = lambda asset: (
    {"tf": {"15m": 0.2, "1h": 0.2, "4h": 0.2}, "price": None,
     "price_source": "STALE", "source_degraded": True}, "LONG")
out = ps.evaluate()
gold = [d for d in out["decisions"] if d["asset"] == "GOLD"][0]
chk("dégradé GOLD -> NO_TRADE malgré un setup présent", gold["grade"] == "NO_TRADE", gold.get("reason"))
chk("price_source propagé dans la décision", gold.get("price_source") == "STALE", str(gold.get("price_source")))
chk("aucun setup attaché en source dégradée", "setup" not in gold)

print("P1b, branche « aucun setup » (non dégradée) propage price_source")
_stub_market()
ps.scanner.scan = lambda: {"setups": [], "regimes": {"GOLD": {"regime": "RANGE"}, "US500": {"regime": "RANGE"}}}
ps._forecast_bias = lambda asset: (
    {"tf": {"15m": 0.0, "1h": 0.0, "4h": 0.0}, "price": 3000,
     "price_source": "yfinance", "source_degraded": False}, "NEUTRAL")
out_ns = ps.evaluate()
for a in ("GOLD", "US500"):
    d = [x for x in out_ns["decisions"] if x["asset"] == a][0]
    chk(f"{a} sans setup -> NO_TRADE", d["grade"] == "NO_TRADE")
    chk(f"{a} sans setup -> price_source propagé", d.get("price_source") == "yfinance", str(d.get("price_source")))
    chk(f"{a} sans setup -> aucun setup attaché", "setup" not in d)

print("Edge, A_SETUP rétrogradé en WATCH par une politique edge ACTIVE non conforme")
_stub_market()
ps.adaptive_edge.current_session = lambda asset, *a, **k: "NY"
ps.position_policy.policy_for = lambda decision: {}
ps.adaptive_edge.matches_decision = lambda decision, policy: {
    "accepted": False, "reason": "hors politique edge active",
    "action": "SKIP", "policy_label": "P", "policy": {}}
ps.scanner.scan = lambda: {
    "setups": [{"asset": "GOLD", "direction": "LONG", "conf": 8.0, "rr": 2.0,
                "entry": 3000, "stop": 2985, "tp": 3030, "regime": "TREND", "strategy": "X"}],
    "regimes": {"GOLD": {"regime": "TREND"}, "US500": {"regime": "TREND"}},
}
ps._forecast_bias = lambda asset: (
    {"tf": {"15m": 0.3, "1h": 0.3, "4h": 0.2}, "price": 3000,
     "price_source": "tradingview", "source_degraded": False}, "LONG")
out_e = ps.evaluate()
ge = [d for d in out_e["decisions"] if d["asset"] == "GOLD"][0]
chk("A_SETUP non conforme à l'edge actif -> WATCH", ge["grade"] == "WATCH", ge.get("grade"))
chk("raison du downgrade propagée", "edge" in (ge.get("reason") or "").lower(), ge.get("reason"))

print()
if FAIL:
    print(f"X ÉCHEC(S): {FAIL}")
    raise SystemExit(1)
print("OK, P4/P4b/P4c (RR souple + garde-fou espérance) + P1/P1b + downgrade edge validés.")
