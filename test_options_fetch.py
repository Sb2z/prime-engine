#!/usr/bin/env python3
"""TEST broutille : gold_options ne fait plus qu'UN seul fetch réseau (avant :
fetch pour le spot + fetch interne d'analyze = 2 appels CBOE). fetch mocké,
aucun réseau."""
import options

FAIL = []


def chk(n, ok, d=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {n}" + (f" — {d}" if d else ""))
    if not ok:
        FAIL.append(n)


calls = {"n": 0}
_orig = options.fetch


def fake_fetch(symbol, **kw):
    calls["n"] += 1
    chain = [
        {"exp": "2099-01-01", "type": "C", "strike": 100.0, "oi": 30, "gamma": 0.1, "iv": 0.2},
        {"exp": "2099-01-01", "type": "P", "strike": 95.0, "oi": 20, "gamma": 0.1, "iv": 0.2},
    ]
    return 100.0, chain


options.fetch = fake_fetch
g = options.gold_options(1000)
chk("gold_options ne fetch qu'UNE fois (plus de double-fetch)", calls["n"] == 1, f"n={calls['n']}")
chk("gold_options renvoie un résultat exploitable", g is not None and g.get("max_pain_u") is not None, str(g))
chk("facteur de conversion appliqué (gold_price/spot)", abs(g.get("factor", 0) - 10.0) < 1e-9, str(g.get("factor")))

# Rétro-compat : analyze sans prefetched fetch toujours (1 fois)
calls["n"] = 0
a = options.analyze("GLD", to_underlying=10.0)
chk("analyze sans prefetched -> fetch (rétro-compat)", calls["n"] == 1, f"n={calls['n']}")
options.fetch = _orig

print()
if FAIL:
    print(f"X ÉCHEC(S): {FAIL}")
    raise SystemExit(1)
print("OK — double-fetch options éliminé, rétro-compat préservée.")
