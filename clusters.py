#!/usr/bin/env python3
"""CLUSTERS — déduplication des signaux IA par position virtuelle.

Le watcher re-signale le même trade à chaque cycle tant que le setup reste
visible (ex.: 7 shorts US500 OTE le 7 juin, pnl identique). Pour les stats,
ces re-signalements sont UNE seule position. Règle :

  Tant qu'un signal racine (asset + direction, trader=AI) est OPEN, tout
  nouveau signal IA identique est un doublon si :
    • son entrée est à moins de 0.35 x ATR15m de l'entrée de la racine
      (plancher 0.15%, la règle anti-doublon historique du journal), OU
    • il est émis moins de 4h après la racine.

En rétroactif, l'heure de clôture exacte des anciens signaux n'est pas
stockée : la racine est présumée ouverte pendant l'horizon d'évaluation (8h),
ou jusqu'à closed_ts si présent (renseigné depuis la migration).

Ce module ne dépend PAS de journal.py (journal.py l'importe).
"""

import datetime as dt
import json

JOURNAL_FILE = "/Users/sam/trading/journal.json"

PRESUMED_OPEN_HOURS = 8.0   # horizon d'évaluation du journal (HORIZON_HOURS)
TIME_RULE_HOURS = 4.0
# Proxy ATR15m en % du prix (ATR1h des moteurs aurum/sentinel500 ≈ 0.40/0.35%
# du prix ; le 15m vaut environ la moitié).
ATR15M_PCT = {"GOLD": 0.20, "US500": 0.175}
PRICE_RULE_FLOOR_PCT = 0.15

DECISIVE = ("WIN", "WIN_TIME", "LOSS", "LOSS_TIME")


def load_journal_raw():
    try:
        with open(JOURNAL_FILE) as f:
            return json.load(f)
    except Exception:
        return {"signals": [], "stats": {}, "last_updated": ""}


def parse_ts(t):
    try:
        ts = dt.datetime.fromisoformat(t.get("ts", ""))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=dt.timezone.utc)
        return ts
    except Exception:
        return dt.datetime.min.replace(tzinfo=dt.timezone.utc)


def is_ai(t):
    trader = t.get("trader") or ("USER" if t.get("source") == "REAL_TRADE" else "AI")
    return trader == "AI"


def entry_proximity_pct(asset):
    return max(0.35 * ATR15M_PCT.get(asset, 0.20), PRICE_RULE_FLOOR_PCT)


def _root_close_ts(root):
    closed = root.get("closed_ts")
    if closed:
        try:
            ts = dt.datetime.fromisoformat(closed)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=dt.timezone.utc)
            return ts
        except Exception:
            pass
    return parse_ts(root) + dt.timedelta(hours=PRESUMED_OPEN_HOURS)


def is_duplicate_of(sig, root):
    """sig est-il un doublon de root (root présumé OPEN à l'émission de sig) ?"""
    if sig.get("asset") != root.get("asset") or sig.get("direction") != root.get("direction"):
        return False
    sig_ts, root_ts = parse_ts(sig), parse_ts(root)
    if sig_ts <= root_ts or sig_ts >= _root_close_ts(root):
        return False
    entry, root_entry = sig.get("entry"), root.get("entry")
    if entry and root_entry:
        if abs(entry - root_entry) / root_entry * 100 < entry_proximity_pct(sig.get("asset")):
            return True
    return (sig_ts - root_ts) < dt.timedelta(hours=TIME_RULE_HOURS)


def annotate(j):
    """Marque duplicate_of sur les signaux IA du journal (en mémoire, in place).

    Respecte les marquages déjà persistés (migration ou log_signal) et
    regroupe rétroactivement le reste avec la même règle.
    """
    ai = sorted((t for t in j.get("signals", []) if is_ai(t)), key=parse_ts)
    roots = []
    for t in ai:
        if t.get("duplicate_of") or t.get("status") == "DUPLICATE":
            continue
        parent = next((r for r in reversed(roots) if is_duplicate_of(t, r)), None)
        if parent is not None:
            t["duplicate_of"] = parent["id"]
        else:
            roots.append(t)
    return j


def _not_dup(t):
    return not t.get("duplicate_of") and t.get("status") != "DUPLICATE"


def non_duplicates(j=None):
    """Tous les signaux du journal, doublons IA exclus (USER jamais dédupliqué)."""
    if j is None:
        j = load_journal_raw()
    annotate(j)
    return [t for t in j.get("signals", []) if _not_dup(t)]


def effective_trades(j=None):
    """Trades clôturés décisifs, doublons exclus — la SEULE source des stats.
    (audit 07-03) session WEEKEND exclue : des « fills » sur prix figés du
    week-end (6 fantômes du 07/06 = 60% du PnL IA) sont des artefacts de
    mesure — aucune décision ne doit s'appuyer dessus."""
    rows = [
        t for t in non_duplicates(j)
        if t.get("status") == "CLOSED" and t.get("result") in DECISIVE
        and t.get("session") != "WEEKEND"
    ]
    rows.sort(key=parse_ts)
    return rows


if __name__ == "__main__":
    j = load_journal_raw()
    sigs = j.get("signals", [])
    ai_closed = [t for t in sigs if is_ai(t) and t.get("status") == "CLOSED"
                 and t.get("result") in DECISIVE]
    eff = effective_trades(j)
    eff_ai = [t for t in eff if is_ai(t)]
    dups = [t for t in sigs if t.get("duplicate_of")]
    print(f"signaux: {len(sigs)} | IA clôturés décisifs bruts: {len(ai_closed)} "
          f"| effectifs: {len(eff_ai)} | doublons: {len(dups)}")
    for t in dups:
        print(f"  DUP {t['id']} ({t.get('paris')}) → {t['duplicate_of']}")
