#!/usr/bin/env python3
"""
USER TRADE CONTEXT — capture le CONTEXTE au moment exact où Sam trade.
═══════════════════════════════════════════════════════════════════════════
But (analyse 2026-06-19) : l'edge de Sam n'est PAS modélisable aujourd'hui car
ses trades n'ont AUCUN contexte capturé (adx/rsi/of_*/session/heure tous NULL).
Ce module relie un trade RÉEL (asset, sens, entrée, HEURE réelle) à la ligne de
features que le watcher a déjà enregistrée à cet instant -> dataset entraînable.

DISCIPLINE STRICTE (sinon le dataset est inutile) :
  • ANTI-LOOKAHEAD : le contexte = la dernière ligne feature_store AVANT (<=) le ts
    du trade. On NE met JAMAIS d'outcome (ret_*) dans le contexte au moment du log.
  • OUTCOME séparé : backfillé APRÈS coup, uniquement depuis des prix POSTÉRIEURS au ts.
  • Lecture seule de la base : on lit feature_exports/*.parquet (jamais prime.duckdb,
    mono-writer verrouillé par le watcher). On écrit notre PROPRE fichier jsonl.

Le contexte LUI-MÊME est déjà capté chaque cycle (~5 min) par feature_store pour
GOLD/US500 ; ce module ne fait que L'APPARIER au vrai trade. Donc le seul vrai
manque restant = l'HEURE RÉELLE du trade (fournie par l'appelant : Telegram/CLI).
"""
import datetime as dt
import json
import os

OUT = "/Users/sam/trading/user_trade_context.jsonl"
FEATURES_PARQUET = "/Users/sam/trading/feature_exports/features.parquet"
# Colonnes d'OUTCOME à NE JAMAIS inclure dans le contexte (anti-lookahead)
_OUTCOME_COLS = {"ret_15m", "ret_1h", "ret_4h", "outcome_quality", "outcome_source"}
HORIZONS = {"ret_15m": 15, "ret_1h": 60, "ret_4h": 240}  # minutes


def _con():
    import duckdb
    return duckdb.connect()  # en mémoire ; lit le parquet, n'ouvre jamais prime.duckdb


def _feature_cols(con, parquet):
    cols = [r[0] for r in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{parquet}')").fetchall()]
    return [c for c in cols if c not in _OUTCOME_COLS]


def capture(asset, direction, entry, ts=None, note="", parquet=FEATURES_PARQUET, out=OUT):
    """Capture le contexte ANTI-LOOKAHEAD d'un trade. ts = heure RÉELLE du trade
    (datetime aware ou ISO) ; None => maintenant (log temps réel). Retourne le dict."""
    if ts is None:
        ts = dt.datetime.now(dt.timezone.utc)
    if isinstance(ts, str):
        ts = dt.datetime.fromisoformat(ts)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=dt.timezone.utc)
    ts_iso = ts.isoformat()
    con = _con()
    fcols = _feature_cols(con, parquet)
    col_list = ", ".join(f'"{c}"' for c in fcols)
    # Dernière ligne AVANT (<=) le ts du trade pour cet actif : c'est le contexte
    # connu à l'instant du trade. Aucune donnée future (anti-lookahead).
    row = con.execute(
        f"SELECT {col_list} FROM read_parquet('{parquet}') "
        f"WHERE asset = ? AND ts <= ? ORDER BY ts DESC LIMIT 1",
        [asset, ts_iso],
    ).fetchone()
    context = dict(zip(fcols, row)) if row else None
    # Garde qualité (audit 07-02) : un prix logué loin du marché (« T GOLD SHORT
    # 4150 » tapé de mémoire alors que l'or est à 4030) fausse TOUS les outcomes
    # (calculés contre entry). On marque, on n'entraîne pas dessus.
    quality = None
    ctx_price = (context or {}).get("price")
    if ctx_price and entry and abs(float(entry) - float(ctx_price)) / float(ctx_price) > 0.005:
        quality = "SUSPECT_ENTRY"
    rec = {
        "id": f"UTC_{asset}_{int(ts.timestamp())}",
        "logged_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "ts": ts_iso, "asset": asset, "direction": direction,
        "entry": float(entry), "note": note, "quality": quality,
        "context_ts": str(context["ts"]) if context else None,
        "context_age_min": (round((ts - dt.datetime.fromisoformat(str(context["ts"]))).total_seconds() / 60, 1)
                            if context and context.get("ts") else None),
        "context": _jsonable(context),
        "outcome": None,   # backfillé plus tard, JAMAIS au moment du log
    }
    with open(out, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
    return rec


def _jsonable(d):
    if not d:
        return None
    return {k: (str(v) if isinstance(v, (dt.datetime, dt.date)) else v) for k, v in d.items()}


def _price_at(con, asset, t_iso, parquet):
    r = con.execute(
        f"SELECT price FROM read_parquet('{parquet}') WHERE asset = ? AND ts >= ? "
        f"ORDER BY ts ASC LIMIT 1", [asset, t_iso]).fetchone()
    return float(r[0]) if r and r[0] is not None else None


def backfill_outcomes(parquet=FEATURES_PARQUET, out=OUT, now=None):
    """Calcule l'outcome des trades capturés dont l'horizon est passé. ANTI-LOOKAHEAD :
    n'utilise QUE des prix POSTÉRIEURS au ts du trade. Réécrit le jsonl."""
    if not os.path.exists(out):
        return 0
    now = now or dt.datetime.now(dt.timezone.utc)
    con = _con()
    recs = [json.loads(l) for l in open(out, encoding="utf-8") if l.strip()]
    n = 0
    for r in recs:
        # audit 07-02 : re-traiter aussi les outcomes PARTIELS (backfill lancé
        # <4h après le trade -> ret_15m seul, jamais complété avant ce fix).
        if set(r.get("outcome") or {}) >= set(HORIZONS) or not r.get("entry"):
            continue
        ts = dt.datetime.fromisoformat(r["ts"]); sign = 1 if r["direction"] == "LONG" else -1
        oc = dict(r.get("outcome") or {})
        prices = {}
        for name, mins in HORIZONS.items():
            if name in oc:
                continue
            t_h = ts + dt.timedelta(minutes=mins)
            if t_h > now:
                continue  # horizon pas encore atteint
            p = _price_at(con, r["asset"], t_h.isoformat(), parquet)
            if p is not None:
                prices[name] = p
                oc[name] = round(sign * (p - r["entry"]) / r["entry"] * 100, 4)
        if oc != (r.get("outcome") or {}):
            # marché fermé (week-end/nuit) : les 3 horizons retombent sur le même
            # premier prix -> outcome dégénéré, à ne pas apprendre.
            if len(prices) >= 3 and len(set(prices.values())) == 1:
                r["quality"] = r.get("quality") or "MARKET_CLOSED"
            r["outcome"] = oc; n += 1
    if n:
        with open(out, "w", encoding="utf-8") as f:
            for r in recs:
                f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
    return n


def summary(out=OUT):
    if not os.path.exists(out):
        return {"captured": 0}
    recs = [json.loads(l) for l in open(out, encoding="utf-8") if l.strip()]
    # comptage HONNÊTE (audits 02-03/07) : records marqués exclus ; contexte plus
    # vieux que 15 min exclu (appariement ts<= sans plafond = contexte du vendredi
    # sur un trade du dimanche) ; et le compteur qui commande le modèle v2 = jours
    # AVEC order-flow (of_delta non-null) — les captures pré-18/06 n'ont pas les
    # features of_* et ne peuvent pas entraîner un modèle qui s'en sert.
    clean = [r for r in recs if not r.get("quality")]
    with_ctx = [r for r in clean if r.get("context")
                and (r.get("context_age_min") is None or r["context_age_min"] <= 15)]
    with_oc = [r for r in with_ctx if r.get("outcome")]
    days = {r["ts"][:10] for r in with_ctx}
    days_of = {r["ts"][:10] for r in with_ctx if r["context"].get("of_delta") is not None}
    return {"captured": len(recs), "exclus_qualite": len(recs) - len(clean),
            "avec_contexte": len(with_ctx),
            "avec_outcome": len(with_oc), "jours_distincts": len(days),
            "jours_distincts_of": len(days_of),
            "pret_pour_modele": len(days_of) >= 15}


if __name__ == "__main__":
    import sys
    a = sys.argv[1:]
    if a and a[0] == "summary":
        print(json.dumps(summary(), indent=2, ensure_ascii=False))
    elif a and a[0] == "backfill":
        print("outcomes backfillés:", backfill_outcomes())
    elif len(a) >= 3:
        # CLI : python user_trade_context.py GOLD SHORT 4150 ["note"]
        note = a[3] if len(a) > 3 else ""
        rec = capture(a[0].upper(), a[1].upper(), float(a[2]), note=note)
        print(f"capturé {rec['id']} | contexte {('OK age '+str(rec['context_age_min'])+'min') if rec['context'] else 'ABSENT'}")
    else:
        print("usage: user_trade_context.py GOLD SHORT 4150 [note] | summary | backfill")
