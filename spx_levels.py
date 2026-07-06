#!/usr/bin/env python3
"""
SENTINEL-500 — Niveaux clés S&P 500 (US500)
Niveaux psychologiques (grille 25/50/100), liquidité, Fibonacci, stops ATR.
"""

def get_key_levels(price: float) -> dict:
    levels = {"psychological": [], "liquidity_above": [], "liquidity_below": [],
              "fib_retrace": [], "proximity_alert": None}

    # Grille S&P : réagit sur les 25, 50, 100 points
    base = int(price / 25) * 25
    grid = [base + o * 25 for o in range(-12, 13) if base + o * 25 > 0]
    near = sorted(grid, key=lambda x: abs(x - price))[:6]
    for lvl in sorted(near):
        strength = "★★★" if lvl % 500 == 0 else ("★★" if lvl % 100 == 0 else "★")
        levels["psychological"].append({
            "level": lvl, "dist": round(lvl - price, 1),
            "dist_pct": round((lvl - price) / price * 100, 2),
            "strength": strength, "side": "above" if lvl > price else "below",
        })

    for lvl in [l for l in near if l % 100 == 0]:
        if lvl > price:
            levels["liquidity_above"].append({"level": lvl + 5, "type": "stop_cluster_longs",
                                              "note": f"Stops acheteurs au-dessus de {lvl}"})
        else:
            levels["liquidity_below"].append({"level": lvl - 5, "type": "stop_cluster_shorts",
                                              "note": f"Stops vendeurs sous {lvl}"})

    all_lvls = [l["level"] for l in levels["psychological"]]
    if all_lvls:
        closest = min(all_lvls, key=lambda x: abs(x - price))
        levels["proximity_alert"] = {"level": closest, "dist": round(closest - price, 1),
                                     "dist_pct": round((closest - price) / price * 100, 2),
                                     "side": "above" if closest > price else "below"}
    return levels


def classify_zone(price: float) -> str:
    n500 = round(price / 500) * 500
    if abs(price - n500) < 8:
        return f"ZONE_MAGNET_FORTE ({n500})"
    n100 = round(price / 100) * 100
    if abs(price - n100) < 5:
        return f"ZONE_MAGNET_MOYENNE ({n100})"
    n50 = round(price / 50) * 50
    if abs(price - n50) < 3:
        return f"ZONE_MAGNET_FAIBLE ({n50})"
    return "ZONE_LIBRE"


def get_fibonacci_levels(swing_high: float, swing_low: float) -> dict:
    diff = swing_high - swing_low
    return {
        "0.0": round(swing_high, 2), "0.236": round(swing_high - 0.236 * diff, 2),
        "0.382": round(swing_high - 0.382 * diff, 2), "0.500": round(swing_high - 0.5 * diff, 2),
        "0.618": round(swing_high - 0.618 * diff, 2), "0.786": round(swing_high - 0.786 * diff, 2),
        "1.000": round(swing_low, 2),
        "1.272": round(swing_low - 0.272 * diff, 2), "1.618": round(swing_low - 0.618 * diff, 2),
    }


def get_atr_stops(price: float, atr: float) -> dict:
    # TP flexibles (pas de RR imposé) : TP1 scalp rapproché, TP2 runner.
    return {
        "stop_long": round(price - 1.5 * atr, 2), "stop_short": round(price + 1.5 * atr, 2),
        "tp1_long": round(price + 1.5 * atr, 2), "tp2_long": round(price + 3.0 * atr, 2),
        "tp1_short": round(price - 1.5 * atr, 2), "tp2_short": round(price - 3.0 * atr, 2),
        "rr_ratio": 1.0, "atr": round(atr, 2),
    }


if __name__ == "__main__":
    p = 7563.0
    print(f"\n📍 Niveaux S&P 500 @ {p}\n")
    lv = get_key_levels(p)
    for l in lv["psychological"]:
        print(f"  {'↑' if l['side']=='above' else '↓'} {l['level']:>6}  ({l['dist']:+.1f}  {l['dist_pct']:+.2f}%)  {l['strength']}")
    print(f"\nZone : {classify_zone(p)}")
