#!/usr/bin/env python3
"""
EDGE ZONE, discipline « reste dans ta zone gagnante ».
═══════════════════════════════════════════════════════════════════════════════
Analyse 2026-06-29 (102 trades réels importés du CSV Revolut) : l'edge de Sam
n'est PAS une question de news, c'est une question de SESSION, de RÉGIME, de SENS
et d'ORDER-FLOW. Mesuré sur ses vrais trades :
  • OR SHORT au marché, session NY, tendance propre  -> il GAGNE (WR ~62%)
  • S&P short / Londres / range / transition          -> il PERD (dérive)

Ce module juge, pour un trade (asset, sens) dans un contexte donné, s'il est DANS
la zone edge ou en DÉRIVE, en s'appuyant sur les STATS RÉELLES (apprend en continu
depuis user_trade_context.jsonl + journal.json, aucune règle figée). Sert :
  • au log Telegram (feedback instantané quand Sam logue « T GOLD SHORT 4150 »)
  • au rapport hebdo de maturation (taux d'adhérence à la zone edge)
  • en CLI avant de trader :  python edge_zone.py GOLD SHORT

Robuste : ne lève jamais (toute erreur -> verdict neutre). Lecture seule.
"""
import json
import os
from collections import defaultdict

import user_trade_context

JOURNAL = "/Users/sam/trading/journal.json"
MIN_N = 5            # n mini dans un bucket pour se fier à sa stat (sinon: inconnu)
BASE_WR = 46.0       # WR15m global de référence (mesuré sur les 94 captures)


def _safe(fn, default):
    try:
        return fn()
    except Exception:
        return default


def _captures():
    out = user_trade_context.OUT
    if not os.path.exists(out):
        return []
    recs = []
    for l in open(out, encoding="utf-8"):
        if not l.strip():
            continue
        try:
            r = json.loads(l)
        except Exception:
            continue
        if r.get("context") and r.get("outcome") and r["outcome"].get("ret_15m") is not None:
            recs.append(r)
    return recs


def _journal_user():
    if not os.path.exists(JOURNAL):
        return []
    j = _safe(lambda: json.load(open(JOURNAL, encoding="utf-8")), {"signals": []})
    return [s for s in j.get("signals", []) if s.get("trader") == "USER" and s.get("status") == "CLOSED"]


def tables():
    """Construit les tables d'edge empiriques (apprises des vrais trades)."""
    recs = _captures()
    sess = defaultdict(list)   # session -> [ret_15m]
    reg = defaultdict(list)    # regime  -> [ret_15m]
    of_hi = []                 # ret_15m quand of_imbalance > 0.6
    for r in recs:
        c = r["context"]; oc = r["outcome"]["ret_15m"]
        if c.get("session"):
            sess[c["session"]].append(oc)
        if c.get("regime"):
            reg[c["regime"]].append(oc)
        imb = c.get("of_imbalance")
        if isinstance(imb, (int, float)) and imb > 0.6:
            of_hi.append(oc)
    # asset x sens : on n'utilise que les trades avec pnl_usd (imports CSV récents,
    # taille réelle). Le $ PONDÉRÉ par la taille est le seul signal honnête : un
    # bucket peut avoir un bon WR mais perdre en $ (pertes plus grosses que les gains
    #, ex. S&P short). pnl_pct non pondéré masquerait cette fuite.
    ad = defaultdict(lambda: [0, 0, 0.0])  # (asset,dir) -> [wins, n, somme_pnl_usd]
    for s in _journal_user():
        pu = s.get("pnl_usd")
        if pu is None:
            continue
        k = (s.get("asset"), s.get("direction"))
        ad[k][1] += 1
        if pu > 0:
            ad[k][0] += 1
        ad[k][2] += pu
    return {
        "session_wr": {k: (sum(1 for x in v if x > 0) / len(v) * 100, len(v)) for k, v in sess.items()},
        "regime_ret": {k: (sum(v) / len(v), len(v)) for k, v in reg.items()},
        "of_hi": (sum(1 for x in of_hi if x > 0) / len(of_hi) * 100, len(of_hi)) if of_hi else (None, 0),
        "assetdir": {k: (v[0] / v[1] * 100 if v[1] else None, v[1], v[2]) for k, v in ad.items()},
        "n_captures": len(recs),
    }


def assess(asset, direction, context):
    """Verdict de zone edge pour (asset, sens) dans `context` (dict feature_store).
    Retourne {verdict, score, reasons:[(signe, texte)], n_captures}. Ne lève jamais."""
    T = _safe(tables, {})
    reasons = []
    score = 0

    # 1) ASSET x SENS, le socle ($ réel mesuré)
    ad = (T.get("assetdir") or {}).get((asset, direction))
    if ad and ad[1] >= MIN_N:
        wr, n, pnl = ad   # pnl = somme des pnl_usd ($ pondéré par la taille)
        if pnl > 0 and wr >= 55:
            score += 2; reasons.append(("✅", f"{asset} {direction} = ton edge (${pnl:+.0f}, WR {wr:.0f}% sur {n})"))
        elif pnl < 0:
            score -= 2; reasons.append(("🔴", f"{asset} {direction} te fait PERDRE (${pnl:+.0f} sur {n}, malgré WR {wr:.0f}%), hors edge"))
        else:
            reasons.append(("➖", f"{asset} {direction} neutre (${pnl:+.0f}, WR {wr:.0f}%)"))
    else:
        reasons.append(("➖", f"{asset} {direction} : pas assez d'historique"))

    # 2) SESSION
    sess = (context or {}).get("session")
    sw = (T.get("session_wr") or {}).get(sess)
    if sess and sw and sw[1] >= MIN_N:
        wr, n = sw
        if wr >= 55:
            score += 1; reasons.append(("✅", f"session {sess} favorable (WR15m {wr:.0f}% sur {n})"))
        elif wr <= 40:
            score -= 1; reasons.append(("🔴", f"session {sess} défavorable (WR15m {wr:.0f}% sur {n})"))
        else:
            reasons.append(("➖", f"session {sess} neutre (WR15m {wr:.0f}%)"))
    elif sess:
        reasons.append(("➖", f"session {sess} (peu de données)"))

    # 3) RÉGIME (le RENDEMENT moyen 15m est plus parlant que le WR ici)
    reg = (context or {}).get("regime")
    rr = (T.get("regime_ret") or {}).get(reg)
    if reg and rr and rr[1] >= MIN_N:
        ret, n = rr
        rshort = reg.split()[0] if reg else reg
        if ret > 0.02:
            score += 1; reasons.append(("✅", f"régime {rshort} porteur (ret15m {ret:+.2f}% sur {n})"))
        elif ret < -0.02:
            score -= 1; reasons.append(("🔴", f"régime {rshort} adverse (ret15m {ret:+.2f}% sur {n})"))
        else:
            reasons.append(("➖", f"régime {rshort} plat (ret15m {ret:+.2f}%)"))
    elif reg:
        reasons.append(("➖", f"régime {reg} (peu de données)"))

    # 4) GRADE DU BOT, INFORMATIF SEULEMENT (vérif adversariale 03-07 : le
    #    candidat « trader les A_SETUP » est RÉFUTÉ, +6,85$ au total recalculé,
    #    signe inversé hors 2 meilleurs jours ; aucun score ne doit en dépendre).
    #    On garde une mise en garde hors-heures-US : mécaniquement, les A_SETUP
    #    du matin étaient les market-entries hors-session du bot (6/6 perdants).
    _US = {"PRE_NY", "NY", "NY_PM", "US_AM", "US_PM", "US_OPEN", "US_CLOSE"}
    grade = (context or {}).get("grade")
    in_us = (context or {}).get("session") in _US
    if grade == "A_SETUP" and not in_us:
        reasons.append(("🔴", "A_SETUP mais HORS heures US, n'en fais PAS une validation "
                              "(les signaux du matin ont coûté −50$ le 30/06)"))
    elif grade:
        reasons.append(("➖", f"grade du bot : {grade} (informatif, non prédictif à ce stade)"))

    # 4bis) VETO ANTI-CHASSE (CONFIRMÉ par les 2 réfuteurs, 03-07) : prix étiré
    #    AU-DESSUS de la Value Area (of_imbalance > +1) -> retours futurs 1h-4h
    #    négatifs sur les 2 actifs (gradient monotone, 8-10 jours sur 10).
    #    Acheter là = acheter le haut du profil de volume.
    imb_now = (context or {}).get("of_imbalance")
    if direction == "LONG" and isinstance(imb_now, (int, float)) and imb_now > 1.0:
        score -= 1
        reasons.append(("🔴", f"ANTI-CHASSE : prix étiré au-dessus de la Value Area "
                              f"(imb {imb_now:.2f} > 1), retour 1h-4h historiquement négatif"))

    # 5) ORDER-FLOW imbalance haut : bonus pour les SHORTS seulement (cohérent
    #    avec la réversion confirmée « imb>+1 -> retours futurs négatifs » ;
    #    pour un LONG c'est le veto anti-chasse du bloc 4bis qui s'applique).
    imb = (context or {}).get("of_imbalance")
    of_hi = T.get("of_hi") or (None, 0)
    if direction == "SHORT" and isinstance(imb, (int, float)):
        if imb > 0.6 and of_hi[0] and of_hi[1] >= MIN_N:
            score += 1; reasons.append(("✅", f"order-flow imbalance haut ({imb:.2f}), WR15m {of_hi[0]:.0f}%"))
        elif imb > 0.6:
            reasons.append(("➕", f"order-flow imbalance haut ({imb:.2f})"))

    verdict = "DANS TA ZONE" if score >= 2 else "DÉRIVE" if score <= -1 else "MARGINAL"
    return {"verdict": verdict, "score": score, "reasons": reasons, "n_captures": T.get("n_captures", 0)}


def live_context(asset):
    """Dernière ligne feature_store pour l'actif (contexte de l'instant). None si indispo."""
    def _q():
        import duckdb
        con = duckdb.connect()
        pq = user_trade_context.FEATURES_PARQUET
        cols = [r[0] for r in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{pq}')").fetchall()]
        row = con.execute(
            f"SELECT * FROM read_parquet('{pq}') WHERE asset = ? ORDER BY ts DESC LIMIT 1", [asset]
        ).fetchone()
        return dict(zip(cols, row)) if row else None
    return _safe(_q, None)


def format_verdict(asset, direction, v):
    icon = {"DANS TA ZONE": "🎯", "MARGINAL": "🟡", "DÉRIVE": "⚠️"}.get(v["verdict"], "•")
    lines = [f"{icon} ZONE EDGE : {v['verdict']} (score {v['score']:+d})"]
    for sign, txt in v["reasons"]:
        lines.append(f"  {sign} {txt}")
    if v["verdict"] == "DÉRIVE":
        lines.append("  → rappel : ton edge est une affaire de SESSION (après-midi US) et de "
                     "RÉGIME, pas d'un actif ou d'un sens fétiche.")
    return "\n".join(lines)


def adherence():
    """Sur les trades capturés : combien étaient DANS la zone vs en DÉRIVE (discipline)."""
    from collections import Counter
    c = Counter()
    for r in _captures():
        a, d, ctx = r.get("asset"), r.get("direction"), (r.get("context") or {})
        if a and d:
            c[assess(a, d, ctx)["verdict"]] += 1
    return c


def weekly_card():
    """Carte d'edge compacte pour le rapport hebdo de maturation. None si pas de données."""
    T = _safe(tables, {})
    ranked = sorted([(k, v) for k, v in (T.get("assetdir") or {}).items() if v[1] >= MIN_N],
                    key=lambda x: -(x[1][2] or 0))
    if not ranked:
        return None
    best, worst = ranked[0], ranked[-1]
    c = adherence(); tot = sum(c.values()) or 1
    lines = ["🎯 CARTE EDGE (apprise de tes trades réels) :",
             f"  edge : {best[0][0]} {best[0][1]} (${best[1][2]:+.0f}, WR {best[1][0]:.0f}% / {best[1][1]})"]
    if worst[1][2] < 0:
        lines.append(f"  fuite: {worst[0][0]} {worst[0][1]} (${worst[1][2]:+.0f} / {worst[1][1]})")
    lines.append(f"  adhérence : {c.get('DANS TA ZONE', 0)}/{tot} DANS ta zone · {c.get('DÉRIVE', 0)} en dérive")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    a = sys.argv[1:]
    if len(a) >= 2:
        asset, direction = a[0].upper(), a[1].upper()
        ctx = live_context(asset) or {}
        v = assess(asset, direction, ctx)
        print(format_verdict(asset, direction, v))
        print(f"\n(contexte live: session={ctx.get('session')} régime={ctx.get('regime')} "
              f"of_imb={ctx.get('of_imbalance')} | {v['n_captures']} captures apprises)")
    else:
        from pprint import pprint
        pprint(tables())
        print("\nusage: python edge_zone.py GOLD SHORT")
