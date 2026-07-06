#!/usr/bin/env python3
"""TEST coûts à l'ENTRÉE (audit 06-18) : le juge facturait le spread seulement à la
sortie (coûts aller-retour ÷2). costs.adjust_entry charge le spread à l'entrée market,
symétriquement à adjust_exit. Pur, aucun réseau."""
import costs

FAIL = []


def chk(n, ok, d=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {n}" + (f", {d}" if d else ""))
    if not ok:
        FAIL.append(n)


lvl = 4000.0
e_long = costs.adjust_entry("GOLD", lvl, "LONG", "SESSION")
e_short = costs.adjust_entry("GOLD", lvl, "SHORT", "SESSION")
x_long = costs.adjust_exit("GOLD", lvl, "LONG", "SESSION", "market")
x_short = costs.adjust_exit("GOLD", lvl, "SHORT", "SESSION", "market")

chk("LONG entre PLUS HAUT que le niveau (ask)", e_long > lvl, f"{e_long} vs {lvl}")
chk("SHORT entre PLUS BAS que le niveau (bid)", e_short < lvl, f"{e_short} vs {lvl}")
chk("entrée et sortie symétriques autour du niveau (LONG)", abs((e_long - lvl) - (lvl - x_long)) < 1e-9,
    f"in +{e_long-lvl:.4f} / out -{lvl-x_long:.4f}")
chk("entrée et sortie symétriques (SHORT)", abs((lvl - e_short) - (x_short - lvl)) < 1e-9)
# Round-trip à plat (acheter ask, vendre bid au même niveau) = perte = spread aller-retour > 0
rt_long = (x_long - e_long) / e_long * 100
chk("round-trip LONG à plat = perte (spread payé 2 fois)", rt_long < 0, f"{rt_long:.4f}%")
chk("spread non nul (sinon coûts inopérants)", e_long > lvl + 0, f"+{e_long-lvl:.4f}")

print()
if FAIL:
    print(f"X ÉCHEC(S): {FAIL}")
    raise SystemExit(1)
print("OK, coûts à l'entrée (spread market) facturés, symétriques à la sortie.")
