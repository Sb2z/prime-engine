#!/usr/bin/env python3
"""UNCERTAINTY, intervalles de confiance pour les stats du journal.

Un WR de 79% sur n=24 veut dire "quelque part entre 59% et 91%". Ce module
rend cette incertitude visible partout où un WR ou une espérance est affiché.

  • wilson(wins, n)            : IC 95% du win rate (borne basse utilisée
                                 par should_replace_user_strategy)
  • bootstrap_exp_by_day(...)  : IC 95% de l'espérance, bootstrap par blocs
                                 JOURNALIERS (les trades d'une même journée
                                 sont autocorrélés, on rééchantillonne les
                                 jours, pas les trades)
"""

import math
import random

MIN_EFFECTIVE_N = 15  # en dessous : ÉCHANTILLON INSUFFISANT
BOOTSTRAP_ITERS = 2000
Z95 = 1.959963984540054


def wilson(wins, n, z=Z95):
    """IC de Wilson 95% du win rate, en %. Retourne (lo, hi) ou None si n=0."""
    if not n:
        return None
    p = wins / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (round(max(0.0, center - half) * 100, 1),
            round(min(1.0, center + half) * 100, 1))


def bootstrap_exp_by_day(trades, iters=BOOTSTRAP_ITERS, seed=42):
    """IC 95% de l'espérance (pnl_pct moyen/trade), bootstrap par jour Paris.

    Retourne (lo, hi) ou None si moins de 2 jours distincts.
    """
    days = {}
    for t in trades:
        day = (t.get("paris") or "")[:10] or (t.get("ts") or "")[:10]
        days.setdefault(day, []).append(t.get("pnl_pct") or 0.0)
    blocks = list(days.values())
    if len(blocks) < 2:
        return None
    rng = random.Random(seed)
    means = []
    for _ in range(iters):
        sample = []
        for _ in range(len(blocks)):
            sample.extend(rng.choice(blocks))
        means.append(sum(sample) / len(sample))
    means.sort()
    return (round(means[int(0.025 * iters)], 3),
            round(means[int(0.975 * iters) - 1], 3))


def fmt_wr(wr, wins, n):
    """Format 'WR 71.4% [IC95 36-92] n=7' avec préfixe si échantillon faible."""
    if wr is None or not n:
        return "WR, (n=0)"
    ci = wilson(wins, n)
    txt = f"WR {wr}% [IC95 {ci[0]}-{ci[1]}] n={n}"
    if n < MIN_EFFECTIVE_N:
        txt = "ÉCHANTILLON INSUFFISANT · " + txt
    return txt


if __name__ == "__main__":
    print("19/24 :", wilson(19, 24))
    print("5/7   :", wilson(5, 7))
    print("45/78 :", wilson(45, 78))
