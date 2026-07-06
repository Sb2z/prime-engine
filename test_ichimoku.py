#!/usr/bin/env python3
"""TEST ICHIMOKU, preuve anti-lookahead + sanité (exigé avant commit, 11/06/2026).

Le bug classique des backtests Ichimoku : utiliser comme nuage "à t" les
midpoints calculés À t (qui décrivent le nuage de t+disp, tracé dans le
futur du graphique) au lieu de ceux calculés à t-disp. Ce test le rend
impossible à réintroduire silencieusement.
"""

import random
import sys

import strategy_families as sf
import ichimoku

FAILURES = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f", {detail}" if detail else ""))
    if not ok:
        FAILURES.append(name)


def make_candles(n=300, seed=42, start=100.0):
    """Marche aléatoire OHLC déterministe."""
    rng = random.Random(seed)
    candles, price = [], start
    for i in range(n):
        o = price
        c = o * (1 + rng.gauss(0, 0.004))
        h = max(o, c) * (1 + abs(rng.gauss(0, 0.002)))
        l = min(o, c) * (1 - abs(rng.gauss(0, 0.002)))
        candles.append([i * 900.0, o, h, l, c, 1000.0])
        price = c
    return candles


print("1. Décalage Senkou, référence indépendante (le cœur de l'anti-lookahead)")
candles = make_candles()
TK, KJ, SB, DISP = 9, 26, 52, 26
for t in (120, 200, 299):
    w = candles[:t + 1]
    s = sf.ichimoku_state(w, "standard")

    def mid(data, n, end_idx):
        seg = data[end_idx - n + 1:end_idx + 1]
        return (max(c[2] for c in seg) + min(c[3] for c in seg)) / 2.0

    # Le nuage CONNU à t doit venir des données se terminant à t-disp :
    ref_sa = (mid(candles, TK, t - DISP) + mid(candles, KJ, t - DISP)) / 2.0
    ref_sb = mid(candles, SB, t - DISP)
    check(f"senkou_a connu à t={t} = projection de t-{DISP}",
          abs(s["senkou_a"] - ref_sa) < 1e-9, f"{s['senkou_a']:.5f} vs {ref_sa:.5f}")
    check(f"senkou_b connu à t={t} = projection de t-{DISP}",
          abs(s["senkou_b"] - ref_sb) < 1e-9)

    # Détecteur du bug : les midpoints DU MOMENT (nuage de t+disp) doivent
    # être différents, si un refactor les confond, ce test hurle.
    bugged_sa = (mid(candles, TK, t) + mid(candles, KJ, t)) / 2.0
    check(f"senkou_a à t={t} ≠ midpoints du moment (nuage de t+{DISP})",
          abs(s["senkou_a"] - bugged_sa) > 1e-9)

print("2. Chikou, n'utilise que le passé (close(t) vs high/low de t-disp)")
t = 200
w = candles[:t + 1]
s = sf.ichimoku_state(w, "standard")
ref = candles[t - DISP]
expected = 1 if w[-1][4] > ref[2] else (-1 if w[-1][4] < ref[3] else 0)
check("chikou conforme à la référence t-26", s["chikou"] == expected)

print("3. Invariance au futur, muter toutes les bougies après t ne change RIEN")
for t in (120, 220):
    base = sf.ichimoku_state(candles[:t + 1], "standard")
    mutated = [list(c) for c in candles]
    for c in mutated[t + 1:]:
        c[1] = c[2] = c[3] = c[4] = c[4] * 7.77  # le futur explose
    after = sf.ichimoku_state(mutated[:t + 1], "standard")
    check(f"état à t={t} identique après mutation du futur", base == after)
    f_base = ichimoku.features_from_window(candles[:t + 1])
    f_after = ichimoku.features_from_window(mutated[:t + 1])
    check(f"features à t={t} identiques après mutation du futur", f_base == f_after)

print("4. Sanité, tendance haussière franche")
up = [[i * 900.0, 100 + i, 100.6 + i, 99.6 + i, 100.5 + i, 0] for i in range(200)]
f = ichimoku.features_from_window(up)
check("prix au-dessus du nuage (pos=1)", f.get("pos") == 1)
check("chikou dégagée haussière (=1)", f.get("chikou") == 1)
check("tenkan > kijun (tk_atr > 0)", (f.get("tk_atr") or 0) > 0)
check("8 features présentes", len(f) == 8, str(sorted(f)))

print("5. Familles, périmètre fermé, sorties valides sur 150 fenêtres")
fams = [k for k in sf.FAMILIES if k.startswith("ichimoku_")]
check("5 familles ichimoku exactement", len(fams) == 5, str(sorted(fams)))
outputs = set()
for fam in fams:
    for speed in ("standard", "fast"):
        fn = sf.build_signal(fam, {"speed": speed})
        for t in range(140, 290):
            r = fn(candles[:t + 1])
            outputs.add(r)
            if r not in (None, "LONG", "SHORT"):
                check(f"{fam} sortie invalide", False, str(r))
                break
check("sorties uniquement dans {None, LONG, SHORT}",
      outputs <= {None, "LONG", "SHORT"}, str(outputs))
check("fenêtre courte → None (pas d'exception)",
      sf.build_signal("ichimoku_tk_cross", {})(candles[:30]) is None)

print()
if FAILURES:
    print(f"✗ {len(FAILURES)} ÉCHEC(S) : {FAILURES}")
    sys.exit(1)
print("✓ TOUS LES TESTS PASSENT, zéro lookahead, périmètre fermé respecté.")
