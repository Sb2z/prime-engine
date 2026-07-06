#!/usr/bin/env python3
"""PAPER SHADOW — évaluation en production des stratégies PAPER du lab.

Le watcher appelle run_shadow() à chaque cycle. Pour chaque stratégie de
research/paper_strategies.json au statut PAPER (la SEULE chose que la
production lit dans research/, et elle n'y entre que tamponnée par le juge) :

  • signal calculé par strategy_families.build_signal — le MÊME code que le
    backtest du harness, aucun écart possible
  • signal → entrée virtuelle journalisée trader=PAPER_<id> ; l'évaluation
    (fills intrabar 1m, coûts, swap) est celle du journal de production
  • AUCUNE alerte Telegram/macOS — shadow strict
  • une seule position virtuelle par stratégie x actif (anti-spam)

Les trades PAPER_* sont exclus des stats IA (trader != "AI") et de la
référence USER. La rétrogradation (harness.check_demotions) est appelée par
le watcher une fois par jour.
"""

import datetime as dt
import json

import datafeed
import journal
import strategy_families

PAPER_FILE = "/Users/sam/trading/research/paper_strategies.json"
KNOWN_ASSETS = ("GOLD", "US500")
WINDOW_BARS = 80
VALID_TF = {"15m", "1h"}


def _papers():
    try:
        with open(PAPER_FILE) as f:
            return [p for p in json.load(f) if p.get("status") == "PAPER"]
    except Exception:
        return []


def _has_open(j, trader, asset):
    return any(s.get("trader") == trader and s.get("asset") == asset
               and s.get("status") == "OPEN" for s in j.get("signals", []))


def _ctx(asset):
    ctx = {}
    try:
        import cot_feed
        snap = cot_feed.snapshot(asset)
        if snap:
            ctx["cot_pctile"] = snap.get("pctile_3y")
    except Exception:
        pass
    return ctx


def run_shadow():
    """Évalue chaque stratégie PAPER. Retourne la liste des entrées loggées."""
    papers = _papers()
    if not papers:
        return []
    j = journal.load_journal()
    logged = []
    candle_cache = {}

    for p in papers:
        tf = p.get("timeframe")
        if tf not in VALID_TF:
            continue
        try:
            fn = strategy_families.build_signal(p["family"], p.get("params"))
        except Exception:
            continue
        exit_rule = p.get("exit_rule") or {}
        stop_pct = float(exit_rule.get("stop_pct", 0.6))
        tp_pct = float(exit_rule.get("tp_pct", 1.0))
        trader = f"PAPER_{p['id']}"

        for asset in p.get("assets", []):
            if asset not in KNOWN_ASSETS:
                continue
            if _has_open(j, trader, asset):
                continue
            key = (asset, tf)
            if key not in candle_cache:
                c = datafeed.get_candles(asset, tf, WINDOW_BARS)
                candle_cache[key] = c["candles"] if c and not c.get("stale") else None
            candles = candle_cache[key]
            if not candles or len(candles) < 10:
                continue
            sig = fn(candles, _ctx(asset))
            if sig not in ("LONG", "SHORT"):
                continue
            lp = float(candles[-1][4])
            sign = 1 if sig == "LONG" else -1
            sid = journal.log_real_trade(
                asset, sig, lp,
                stop=lp * (1 - sign * stop_pct / 100),
                tp1=lp * (1 + sign * tp_pct / 100),
                trader=trader,
                note=f"shadow {p['family']} {json.dumps(p.get('params'), sort_keys=True)}",
                valid_hours=float(exit_rule.get("horizon_bars", 32))
                            * (0.25 if tf == "15m" else 1.0),
            )
            j = journal.load_journal()  # recharge après écriture
            logged.append({"strategy": p["id"], "asset": asset,
                           "direction": sig, "signal_id": sid})
    return logged


if __name__ == "__main__":
    out = run_shadow()
    print(json.dumps({"papers_actives": len(_papers()), "entrees": out},
                     ensure_ascii=False, indent=1))
