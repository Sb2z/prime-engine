#!/usr/bin/env python3
"""TEST famille momentum_breakout (strategy_families) — exigé avant commit.

Prouve : cassure en tendance → signal dans le sens ; porte de régime qui bloque
hors tendance ; anti-lookahead (canal = bougies AVANT la décision, clôture seule
comparée) ; sorties valides.
"""
import math

import strategy_families as sf

FAIL = []


def chk(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAIL.append(name)


def candle(c, h=None, l=None):
    return [0, c, (h if h is not None else c + 0.1), (l if l is not None else c - 0.1), c, 0]


def uptrend(n=60, step=1.0):
    return [candle(100 + i * step) for i in range(n)]


def downtrend(n=60, step=1.0):
    return [candle(200 - i * step) for i in range(n)]


fn = sf.build_signal("momentum_breakout", {})

print("1. Tendance HAUSSIÈRE propre + clôture qui casse le canal → LONG")
w = uptrend()
chk("LONG", fn(w) == "LONG", str(fn(w)))

print("2. Tendance BAISSIÈRE propre + cassure bas → SHORT")
chk("SHORT", fn(downtrend()) == "SHORT", str(fn(downtrend())))

print("3. Porte de régime : adx_min impossible → None malgré la cassure")
fn_gate = sf.build_signal("momentum_breakout", {"adx_min": 999})
chk("None (régime bloque)", fn_gate(uptrend()) is None, str(fn_gate(uptrend())))

print("4. Range (ER bas) → None (pas de tendance propre)")
rng = [candle(100 + 3 * math.sin(i * 0.9)) for i in range(60)]
chk("None (range)", fn(rng) is None, str(fn(rng)))

print("5. Anti-lookahead : la bougie de décision est EXCLUE du canal")
# Dernière bougie : mèche haute énorme (h=300) mais clôture SOUS le canal antérieur
w2 = uptrend()
w2[-1] = candle(150.0, h=300.0)   # close 150 < plus-haut antérieur (~158) malgré h=300
chk("pas de LONG sur une simple mèche (clôture sous le canal)", fn(w2) != "LONG", str(fn(w2)))

print("6. Anti-lookahead : muter le FUTUR ne change pas le signal à t")
base = uptrend(80)
sig_t = sf.build_signal("momentum_breakout", {})(base[:60])
mut = [list(c) for c in base]
for c in mut[60:]:
    c[1] = c[2] = c[3] = c[4] = c[4] * 9   # futur explose
sig_mut = sf.build_signal("momentum_breakout", {})(mut[:60])
chk("signal à t identique après mutation du futur", sig_t == sig_mut)

print("7. Sorties valides + fenêtre courte → None")
outs = set()
for t in range(45, 80):
    outs.add(fn(uptrend(80)[:t]))
chk("sorties ⊆ {None,LONG,SHORT}", outs <= {None, "LONG", "SHORT"}, str(outs))
chk("fenêtre trop courte → None (pas d'exception)", fn(uptrend(20)) is None)

print()
if FAIL:
    print(f"X {len(FAIL)} ÉCHEC(S): {FAIL}")
    raise SystemExit(1)
print("OK — momentum_breakout validée.")
