#!/usr/bin/env python3
"""PARITÉ PINE vs PYTHON, le test qui valide le déploiement TradingView.

Compare, au même instant, l'état du trend day trigger calculé par :
  • le Python de référence (datafeed + tv_candles.compute_ta + regime +
    trend_day_trigger, fonctions importées, jamais réimplémentées)
  • l'indicateur Pine sur le chart TradingView Desktop (plots PARITY_* lus
    dans la data window via le CLI du MCP claudeverstradingview)

Tolérances : |ΔADX| <= 1.5 (seeding Wilder différent sur ~60 barres),
|ΔER| <= 0.02, directions et état armé STRICTEMENT identiques.
Règle de référence : si ça diverge au-delà, on corrige le PINE, jamais le
Python (c'est lui qui porte l'historique du forward-test).

Écrit pine_parity_status.json à chaque run, le watcher ne fait que LIRE ce
fichier (découplage total : aucun import CDP dans la boucle autonome).

Usage : python3 scripts/compare_pine_parity.py   (TradingView Desktop ouvert
        avec le port debug : tools/claudeverstradingview/scripts/launch_tv_debug_mac.sh)
"""

import datetime as dt
import json
import subprocess
import sys
import time

sys.path.insert(0, "/Users/sam/trading")

import datafeed
import regime
import trend_day_trigger
from tv_candles import SYMBOL_MAP

KASPER = ["node", "/Users/sam/trading/tools/claudeverstradingview/src/cli/index.js"]
STATUS_FILE = "/Users/sam/trading/pine_parity_status.json"
ASSETS = ("GOLD", "US500")
TOL_ADX = 1.5
TOL_ER = 0.02
CHART_SETTLE_S = 6  # request.security 15m+1h après changement de symbole

DIR_NUM = {1: "LONG", -1: "SHORT", 0: "NEUTRAL"}


def _to_float(value):
    """Nombre TradingView → float, en gérant la locale FR de l'UI :
    espaces fines de milliers, virgule décimale, moins typographique U+2212."""
    s = str(value)
    for ch in (" ", " ", " "):
        s = s.replace(ch, "")
    return float(s.replace("−", "-").replace(",", "."))


def kasper(*args, timeout=45):
    r = subprocess.run(KASPER + list(args), capture_output=True, text=True, timeout=timeout)
    # Le CLI écrit le JSON sur stdout en succès, sur stderr en erreur
    for raw in (r.stdout.strip(), r.stderr.strip()):
        start = raw.find("{")
        if start >= 0:
            try:
                return json.loads(raw[start:])
            except json.JSONDecodeError:
                continue
    raise RuntimeError(f"sortie CLI illisible: {r.stdout[:200]} {r.stderr[:200]}")


def write_status(payload):
    payload["ts"] = dt.datetime.now(dt.timezone.utc).isoformat()
    with open(STATUS_FILE, "w") as f:
        json.dump(payload, f, indent=1, ensure_ascii=False)


def python_side(asset):
    # 150 barres 15m : réduit l'écart de seeding Wilder vs le Pine qui a tout
    # l'historique (piège documenté dans MISSION_PINE_TRIGGER.md). L'ER reste
    # calculé sur les 40 derniers closes (regime.detect, lookback=40).
    c15 = datafeed.get_candles(asset, "15m", 150)
    c1h = datafeed.get_candles(asset, "1h", 100)
    if not c15 or c15.get("stale") or not c1h or c1h.get("stale"):
        raise RuntimeError(f"{asset}: bougies indisponibles côté Python")
    if c15["source"] != "tradingview":
        raise RuntimeError(f"{asset}: source {c15['source']} != tradingview, parité "
                           f"impossible (le Pine lit le feed TradingView)")
    ta15 = trend_day_trigger._ta(c15["candles"])
    ta1h = trend_day_trigger._ta(c1h["candles"])
    rg = regime.detect(c15["candles"], adx=ta15["adx"])
    d15 = trend_day_trigger._tf_direction(ta15)
    d1h = trend_day_trigger._tf_direction(ta1h)
    er = rg.get("er") or 0.0
    armed = (ta15["adx"] > trend_day_trigger.ARM_ADX and er > trend_day_trigger.ARM_ER
             and d15 != "NEUTRAL" and d15 == d1h)
    return {"adx": round(ta15["adx"], 2), "er": round(er, 3),
            "dir15": d15, "dir1h": d1h, "armed": bool(armed)}


def _collect_parity_values(obj, found):
    """Cherche récursivement les plots PARITY_* dans la sortie de `values`."""
    if isinstance(obj, dict):
        name = obj.get("name") or obj.get("title") or ""
        value = obj.get("value")
        if isinstance(name, str) and name.startswith("PARITY_") and value is not None:
            try:
                found[name] = _to_float(value)
            except ValueError:
                pass
        for k, v in obj.items():
            if isinstance(k, str) and k.startswith("PARITY_") and isinstance(v, (int, float, str)):
                try:
                    found[k] = _to_float(v)
                except ValueError:
                    pass
            _collect_parity_values(v, found)
    elif isinstance(obj, list):
        for it in obj:
            _collect_parity_values(it, found)


def pine_set_chart(asset):
    """Bascule le chart sur l'actif et laisse request.security se recharger."""
    kasper("symbol", SYMBOL_MAP[asset])
    kasper("timeframe", "15")
    time.sleep(CHART_SETTLE_S)


def pine_side(asset):
    vals = kasper("values")
    found = {}
    _collect_parity_values(vals, found)
    needed = ("PARITY_adx15", "PARITY_er15", "PARITY_dir15", "PARITY_dir1h", "PARITY_armed")
    missing = [k for k in needed if k not in found]
    if missing:
        raise RuntimeError(
            f"plots manquants dans la data window: {missing}. "
            f"L'indicateur Prime Trend Day Trigger est-il bien sur le chart ? "
            f"Sortie brute: {json.dumps(vals)[:400]}")
    return {"adx": round(found["PARITY_adx15"], 2),
            "er": round(found["PARITY_er15"], 3),
            "dir15": DIR_NUM.get(int(found["PARITY_dir15"]), "?"),
            "dir1h": DIR_NUM.get(int(found["PARITY_dir1h"]), "?"),
            "armed": bool(int(found["PARITY_armed"]))}


def compare(py, pn):
    checks = {
        "adx": abs(py["adx"] - pn["adx"]) <= TOL_ADX,
        "er": abs(py["er"] - pn["er"]) <= TOL_ER,
        "dir15": py["dir15"] == pn["dir15"],
        "dir1h": py["dir1h"] == pn["dir1h"],
        "armed": py["armed"] == pn["armed"],
    }
    return checks, all(checks.values())


def main():
    try:
        st = kasper("status")
        if not st.get("success"):
            raise RuntimeError(st.get("error", "CDP KO"))
    except Exception as exc:
        write_status({"status": "NO_CDP", "pass": False, "error": str(exc)})
        print("✗ TradingView Desktop sans port debug. Lancer :")
        print("  /Users/sam/trading/tools/claudeverstradingview/scripts/launch_tv_debug_mac.sh")
        sys.exit(2)

    results = {}
    all_pass = True
    for asset in ASSETS:
        try:
            # Chart d'abord, puis fetch Python et lecture Pine dos à dos :
            # minimiser l'écart temporel (la bougie en cours bouge).
            pine_set_chart(asset)
            py = python_side(asset)
            pn = pine_side(asset)
            checks, ok = compare(py, pn)
        except Exception as exc:
            results[asset] = {"error": str(exc)}
            all_pass = False
            print(f"\n{asset}: ERREUR, {exc}")
            continue
        all_pass &= ok
        results[asset] = {"python": py, "pine": pn, "checks": checks, "pass": ok}
        print(f"\n  {asset}, {'PASS ✅' if ok else 'FAIL ❌'}")
        print(f"  {'':8} {'Python':>10} {'Pine':>10}  ok")
        for k in ("adx", "er", "dir15", "dir1h", "armed"):
            print(f"  {k:8} {str(py[k]):>10} {str(pn[k]):>10}  {'✓' if checks[k] else '✗'}")

    write_status({"status": "PASS" if all_pass else "FAIL",
                  "pass": all_pass, "results": results})
    print(f"\nVerdict global : {'PASS' if all_pass else 'FAIL'} → {STATUS_FILE}")
    if not all_pass:
        print("Rappel : on corrige le PINE, jamais le Python (référence forward-test).")
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
