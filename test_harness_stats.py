#!/usr/bin/env python3
"""TEST intégrité statistique du juge (audit 2026-06-17) : P5 t-stat par JOUR,
P6 Bonferroni GLOBAL. Isolé : registry() mocké, aucun effet sur le vrai lab."""
import harness

FAIL = []


def chk(n, ok, d=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {n}" + (f", {d}" if d else ""))
    if not ok:
        FAIL.append(n)


print("P6, Bonferroni GLOBAL (déflation sur le total des tests, pas par famille)")
orig = harness.registry
harness.registry = lambda: [{"family": "a"} for _ in range(5)]
z_a, _, n_a = harness.required_z("momentum")
z_b, _, n_b = harness.required_z("cot_extreme")   # autre famille
chk("n identique quelle que soit la famille (global)", n_a == n_b == 6, f"{n_a}/{n_b}")
harness.registry = lambda: [{"family": "a"} for _ in range(20)]
z_20, _, n_20 = harness.required_z("x")
chk("plus de tests à vie -> seuil z plus dur", z_20 > z_a and n_20 == 21, f"z {z_a:.2f}->{z_20:.2f}")
harness.registry = orig

print("P5, t-stat par JOUR (dégonfle l'autocorrélation intraday)")
trades = [{"pnl_pct": 1.0, "paris": "2026-06-10 10:00"} for _ in range(5)]
trades += [{"pnl_pct": -0.5, "paris": "2026-06-11 11:00"} for _ in range(5)]
t_trade = harness._tstat([t["pnl_pct"] for t in trades])
dm = harness._daily_means(trades)
t_day = harness._tstat(dm)
chk("moyennes journalières = 2 valeurs (2 jours)", sorted(dm) == [-0.5, 1.0], str(dm))
chk("|t| par-jour < |t| par-trade", abs(t_day) < abs(t_trade), f"jour={t_day:.2f} trade={t_trade:.2f}")

print()
if FAIL:
    print(f"X ÉCHEC(S): {FAIL}")
    raise SystemExit(1)
print("OK, intégrité du juge (P5 + P6) validée.")
