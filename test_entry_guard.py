#!/usr/bin/env python3
"""TEST garde-fou de distance d'entree (scanner.quality_setup, 2026-06-16).

Prouve qu'une entree OTE lointaine est ramenee a <= MAX_ENTRY_ATR x ATR15m du
prix, du bon cote, en conservant le RR >= 2.
"""
import clusters
import scanner

FAIL = []


def chk(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f", {detail}" if detail else ""))
    if not ok:
        FAIL.append(name)


def base_R(asset, price, direction, sweet_spot, stop):
    return {
        "price": price,
        "confluence": {"score": 8.0, "direction": direction, "aligned": "8/8"},
        "strategy": {"name": "OTE_RETRACEMENT",
                     "ote": {"sweet_spot": sweet_spot},
                     "levels": {"entry": sweet_spot, "stop": stop}},
        "regime_scalp": {"regime": "TEST"},
        "macro": {}, "options": {}, "orderflow": {}, "fibs": {},
    }


def cap_for(asset, price):
    atr = price * clusters.ATR15M_PCT.get(asset, 0.20) / 100
    return scanner.MAX_ENTRY_ATR * atr


print("1. SHORT avec entree OTE TRES au-dessus du prix (repli injoignable)")
asset, price = "US500", 7430.0
R = base_R(asset, price, "SHORT", sweet_spot=7560.0, stop=7600.0)  # entree +1.75%, loin
s = scanner.quality_setup(R, asset)
cap = cap_for(asset, price)
chk("setup produit", s is not None)
if s:
    chk("entry_capped=True", s.get("entry_capped") is True)
    chk("entree a portee (<= cap du prix)", abs(s["entry"] - price) <= cap + 0.05,
        f"|{s['entry']}-{price}|={abs(s['entry']-price):.2f} cap={cap:.2f}")
    chk("entree du bon cote (SHORT => au-dessus du prix)", s["entry"] >= price)
    chk("RR >= 2", s["rr"] >= 2.0, f"rr={s['rr']}")
    chk("stop = invalidation volatilité au-dessus de l'entrée (SHORT)", s["stop"] > s["entry"])

print("2. LONG avec entree OTE TRES sous le prix")
asset, price = "GOLD", 4300.0
R = base_R(asset, price, "LONG", sweet_spot=4230.0, stop=4200.0)  # entree -1.6%
s = scanner.quality_setup(R, asset)
cap = cap_for(asset, price)
chk("setup produit", s is not None)
if s:
    chk("entry_capped=True", s.get("entry_capped") is True)
    chk("entree a portee (<= cap)", abs(s["entry"] - price) <= cap + 0.05,
        f"|{s['entry']}-{price}|={abs(s['entry']-price):.2f} cap={cap:.2f}")
    chk("entree du bon cote (LONG => sous le prix)", s["entry"] <= price)
    chk("RR >= 2", s["rr"] >= 2.0, f"rr={s['rr']}")
    chk("stop sous l'entree (LONG)", s["stop"] < s["entry"])

print("3. Entree DEJA proche (<= cap) : pas de modification")
asset, price = "US500", 7430.0
near = round(price - 0.5 * (price * clusters.ATR15M_PCT.get(asset, 0.20) / 100), 2)
R = base_R(asset, price, "LONG", sweet_spot=near, stop=near - 20)
s = scanner.quality_setup(R, asset)
chk("setup produit", s is not None)
if s:
    chk("entry_capped=False (deja proche)", s.get("entry_capped") is False)

print("4. TP cap : cible structurelle TRES loin (fib du range jour) ramenee")
asset, price = "US500", 7430.0
R = base_R(asset, price, "LONG", sweet_spot=7420.0, stop=7400.0)
R["fibs"] = {"ext": 7800.0}  # cible lointaine (+5%) injoignable en intraday
s = scanner.quality_setup(R, asset)
atr = price * clusters.ATR15M_PCT.get(asset, 0.20) / 100
chk("setup produit", s is not None)
if s:
    chk("tp_capped=True", s.get("tp_capped") is True)
    chk("TP <= MAX_TP_ATR x ATR15m du prix d'entree",
        abs(s["tp"] - s["entry"]) <= scanner.MAX_TP_ATR * atr + 0.05,
        f"dist={abs(s['tp']-s['entry']):.1f} max={scanner.MAX_TP_ATR*atr:.1f}")
    chk("TP intraday réaliste (<2% du prix)", abs(s["tp"] - price) / price < 0.02,
        f"tp={s['tp']} ({(s['tp']-price)/price*100:+.2f}%)")
    chk("RR >= 2 préservé", s["rr"] >= 2.0, f"rr={s['rr']}")

print("5. TP proche (deja realiste) : inchange")
asset, price = "US500", 7430.0
R = base_R(asset, price, "LONG", sweet_spot=7420.0, stop=7400.0)
R["fibs"] = {"near": 7480.0}  # cible a +0.67%, RR (60/20)=3, sous le plafond
s = scanner.quality_setup(R, asset)
chk("setup produit", s is not None)
if s:
    chk("tp_capped=False (deja realiste)", s.get("tp_capped") is False)
    chk("TP = la cible logique (7480)", abs(s["tp"] - 7480.0) < 0.05, f"tp={s['tp']}")

print("6. RR ~1.5 (avant rejeté car <2) : ACCEPTÉ maintenant (plancher santé 1.0)")
asset, price = "US500", 7430.0
R = base_R(asset, price, "LONG", sweet_spot=7420.0, stop=7400.0)  # risk 20
R["fibs"] = {"t": 7450.0}  # cible +0.27%, RR = 30/20 = 1.5
s = scanner.quality_setup(R, asset)
chk("plancher abaissé à 1.0", scanner.RR_MIN_SETUP == 1.0)
chk("setup ACCEPTÉ (n'est plus rejeté à RR 1.5)", s is not None)
if s:
    chk("RR ~1.5 (contextuel, pas forcé à 2)", 1.4 <= s["rr"] <= 1.6, f"rr={s['rr']}")
    chk("TP = la cible logique 7450", abs(s["tp"] - 7450.0) < 0.05, f"tp={s['tp']}")

print("7. TENDANCE PROPRE + fenêtre NY : entrée OTE lointaine ramenée AU MARCHÉ (fix NOFILL 06-22)")
asset, price = "GOLD", 4150.0
R = base_R(asset, price, "SHORT", sweet_spot=4175.0, stop=4190.0)  # repli OTE +0.6%
R["regime_scalp"] = {"regime": "TENDANCE PROPRE 🟢"}
_real_hour = scanner._paris_hour
scanner._paris_hour = lambda: 16          # dans la fenêtre NY (déterministe)
s = scanner.quality_setup(R, asset)
chk("setup produit", s is not None)
if s:
    chk("entry_capped=True", s.get("entry_capped") is True)
    chk("entrée ~AU MARCHÉ en tendance (|entry-price|~0)", abs(s["entry"] - price) <= 0.05,
        f"entry={s['entry']} price={price}")
    chk("stop = invalidation volatilité au-dessus (SHORT)", s["stop"] > s["entry"])

print("7b. TENDANCE PROPRE mais HORS fenêtre NY (audit 07-02) : repli OTE conservé")
scanner._paris_hour = lambda: 3           # nuit, mesuré : 6 fills marché hors-NY = 6 pertes
s = scanner.quality_setup(R, asset)
scanner._paris_hour = _real_hour
chk("setup produit", s is not None)
if s:
    chk("PAS d'entrée-marché la nuit (repli au-dessus du prix)", s["entry"] > price + 1.0,
        f"entry={s['entry']} price={price}")

print("8. RANGE : le repli OTE est CONSERVÉ (pas de market entry)")
asset, price = "GOLD", 4150.0
R = base_R(asset, price, "SHORT", sweet_spot=4175.0, stop=4190.0)
R["regime_scalp"] = {"regime": "RANGE ⚪"}
s = scanner.quality_setup(R, asset)
cap = cap_for(asset, price)
chk("setup produit", s is not None)
if s:
    chk("entrée GARDE le repli (au-dessus du prix)", s["entry"] > price + 1.0, f"entry={s['entry']} price={price}")
    chk("entrée à distance du cap (>= cap*0.8)", abs(s["entry"] - price) >= cap * 0.8,
        f"dist={abs(s['entry']-price):.2f} cap={cap:.2f}")

print()
if FAIL:
    print(f"X {len(FAIL)} ECHEC(S): {FAIL}")
    raise SystemExit(1)
print("OK, garde-fou de distance valide.")
