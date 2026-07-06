#!/usr/bin/env python3
"""
Gold AI — Niveaux clés : psychologiques, liquidité, zones institutionnelles
Logique Smart Money Concepts (SMC) + zones de Fibonacci + ATH/ATL
"""

def get_key_levels(price: float) -> dict:
    """
    Calcule tous les niveaux clés autour du prix actuel.
    Retourne un dict structuré avec catégories et distances.
    """

    levels = {
        "psychological": [],   # Niveaux ronds $X000, $X500, $X250
        "liquidity_above": [], # Stop-loss clusters au-dessus (longs en danger)
        "liquidity_below": [], # Stop-loss clusters en-dessous (shorts en danger)
        "fib_retrace": [],     # Retracements Fibonacci depuis swing récent
        "proximity_alert": None,  # Niveau le plus proche
    }

    # ── Niveaux psychologiques (round numbers) ────────────────────────────────
    # Gold réagit fortement sur les 00, 50, 500
    psycho_grid = []
    base = int(price / 50) * 50
    for offset in range(-10, 11):
        lvl = base + offset * 50
        if lvl > 0:
            psycho_grid.append(lvl)

    # Filtrer les 6 plus proches
    psycho_sorted = sorted(psycho_grid, key=lambda x: abs(x - price))[:6]
    for lvl in sorted(psycho_sorted):
        dist = round(lvl - price, 1)
        dist_pct = round((lvl - price) / price * 100, 2)
        strength = "★★★" if lvl % 500 == 0 else ("★★" if lvl % 100 == 0 else "★")
        levels["psychological"].append({
            "level": lvl,
            "dist": dist,
            "dist_pct": dist_pct,
            "strength": strength,
            "side": "above" if lvl > price else "below"
        })

    # ── Zones de liquidité (clusters de stops) ────────────────────────────────
    # Logique : les stops s'accumulent juste au-dessus des résistances récentes
    # et juste en-dessous des supports récents → cibles institutionnelles
    #
    # Approximation : les niveaux ronds forts + 2-5$ = zone de stops retail
    for lvl in [l for l in psycho_sorted if l % 100 == 0]:
        if lvl > price:
            levels["liquidity_above"].append({
                "level": round(lvl + 3, 0),
                "type": "stop_cluster_longs",
                "note": f"Stops acheteurs au-dessus de ${lvl}"
            })
        else:
            levels["liquidity_below"].append({
                "level": round(lvl - 3, 0),
                "type": "stop_cluster_shorts",
                "note": f"Stops vendeurs sous ${lvl}"
            })

    # ── Niveau le plus proche ─────────────────────────────────────────────────
    all_lvls = [l["level"] for l in levels["psychological"]]
    if all_lvls:
        closest = min(all_lvls, key=lambda x: abs(x - price))
        dist = round(closest - price, 1)
        levels["proximity_alert"] = {
            "level": closest,
            "dist": dist,
            "dist_pct": round(dist / price * 100, 2),
            "side": "above" if closest > price else "below"
        }

    return levels


def classify_zone(price: float) -> str:
    """
    Détermine si le prix est dans une zone psychologiquement significative.
    """
    # Proches d'un niveau $X000 (±$15)
    nearest_1000 = round(price / 1000) * 1000
    if abs(price - nearest_1000) < 15:
        return f"ZONE_MAGNET_FORTE (${nearest_1000})"

    # Proches d'un niveau $X500 (±$10)
    nearest_500 = round(price / 500) * 500
    if abs(price - nearest_500) < 10:
        return f"ZONE_MAGNET_MOYENNE (${nearest_500})"

    # Proches d'un niveau $X00 (±$5)
    nearest_100 = round(price / 100) * 100
    if abs(price - nearest_100) < 5:
        return f"ZONE_MAGNET_FAIBLE (${nearest_100})"

    return "ZONE_LIBRE"


def get_fibonacci_levels(swing_high: float, swing_low: float) -> dict:
    """
    Calcule les retracements et extensions Fibonacci classiques.
    swing_high / swing_low = derniers sommets/creux significatifs.
    """
    diff = swing_high - swing_low
    fibs = {
        "0.0":   round(swing_high, 2),
        "0.236": round(swing_high - 0.236 * diff, 2),
        "0.382": round(swing_high - 0.382 * diff, 2),
        "0.500": round(swing_high - 0.500 * diff, 2),
        "0.618": round(swing_high - 0.618 * diff, 2),
        "0.786": round(swing_high - 0.786 * diff, 2),
        "1.000": round(swing_low, 2),
        # Extensions
        "1.272": round(swing_low - 0.272 * diff, 2),
        "1.618": round(swing_low - 0.618 * diff, 2),
    }
    return fibs


def get_atr_stops(price: float, atr: float) -> dict:
    """
    Calcule les stops basés sur l'ATR (volatilité réelle).
    Méthode institutionnelle : 1.5× ATR pour stop, 3× ATR pour TP.
    """
    # TP flexibles (pas de RR imposé) : TP1 scalp rapproché, TP2 runner.
    # La décision vient de l'analyse globale, pas du ratio.
    return {
        "stop_long":  round(price - 1.5 * atr, 2),
        "stop_short": round(price + 1.5 * atr, 2),
        "tp1_long":   round(price + 1.5 * atr, 2),   # scalp/quick
        "tp2_long":   round(price + 3.0 * atr, 2),   # runner
        "tp1_short":  round(price - 1.5 * atr, 2),
        "tp2_short":  round(price - 3.0 * atr, 2),
        "rr_ratio":   1.0,
        "atr":        round(atr, 2),
    }


# ── Test direct ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    price = 4390.0
    print(f"\n📍 Niveaux clés pour GOLD @ ${price}\n")

    levels = get_key_levels(price)
    print("Niveaux psychologiques :")
    for l in levels["psychological"]:
        arrow = "↑" if l["side"] == "above" else "↓"
        print(f"  {arrow} ${l['level']:>6}  ({l['dist']:+.1f}$  {l['dist_pct']:+.2f}%)  {l['strength']}")

    print(f"\nZone actuelle : {classify_zone(price)}")
    print(f"Niveau le plus proche : ${levels['proximity_alert']['level']} "
          f"({levels['proximity_alert']['dist']:+.1f}$)")

    print("\nLiquidités au-dessus :")
    for l in levels["liquidity_above"]:
        print(f"  ↑ ${l['level']}  — {l['note']}")

    print("\nLiquidités en-dessous :")
    for l in levels["liquidity_below"]:
        print(f"  ↓ ${l['level']}  — {l['note']}")

    print("\nFibonacci (swing $4539 → $4366) :")
    fibs = get_fibonacci_levels(4539, 4366)
    for k, v in fibs.items():
        marker = " ←← PRIX" if abs(v - price) < 10 else ""
        print(f"  Fib {k:>5} : ${v}{marker}")

    print("\nStops ATR (ATR estimé = $25) :")
    stops = get_atr_stops(price, 25)
    for k, v in stops.items():
        print(f"  {k:>12} : {v}")
