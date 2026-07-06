#!/usr/bin/env python3
"""HARNESS — LE JUGE du Prime Research Lab. GELÉ après création.

Ce fichier est protégé par le hook constitutionnel (.githooks/pre-commit) :
le chercheur autonome ne peut pas le modifier. Il ne dépend que de modules
eux-mêmes protégés (costs, strategy_families) — l'incertitude (bootstrap)
est implémentée ICI pour que le juge soit autosuffisant.

Verdicts : KILLED (attendu ~95% des cas) ou PAPER. Jamais de promotion LIVE
ici — seul Sam promeut (pipeline MISSION_V3).

Règles immuables appliquées à TOUTE stratégie :
  • walk-forward 3 fenêtres chronologiques, purge 1 jour entre les blocs,
    le verdict ne regarde QUE les fenêtres de test
  • coûts systématiques (costs.py) : spread session/off, slippage, swap
  • une seule position à la fois par actif (équivalent dédup production)
  • homogénéité de source des données (garde anti-basis V2)
  • correction de comparaisons multiples À VIE : alpha = 0.05 / nb de tests
    déjà enregistrés dans la famille (registry append-only) — tester plus
    durcit le seuil automatiquement
  • PAPER exige : n effectif >= 30, espérance test nette > 0 sur >= 2/3
    fenêtres, borne basse IC bootstrap-jours > 0, t-stat >= z(alpha déflaté)
"""

import datetime as dt
import tz
import hashlib
import json
import math
import os
import random
from statistics import NormalDist

import costs
import strategy_families

RESEARCH = "/Users/sam/trading/research"
REGISTRY_FILE = os.path.join(RESEARCH, "hypothesis_registry.json")
VERDICTS_DIR = os.path.join(RESEARCH, "verdicts")
PAPER_FILE = os.path.join(RESEARCH, "paper_strategies.json")

N_WINDOWS = 3
PURGE_BARS = {"1m": 1440, "5m": 288, "15m": 96, "1h": 24, "1d": 1}  # ~1 jour
MIN_EFF_N = 30
MIN_WINDOWS_POS = 2
BASE_ALPHA = 0.05
BOOT_ITERS = 2000
DEMOTE_WINDOW = 30  # rétrogradation : borne haute IC < 0 sur 30 trades glissants

WARMUP_BARS = 60  # le signal ne voit jamais moins de 60 bougies d'historique


# ── Registry (append-only) ───────────────────────────────────────────────────
def _load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def registry():
    return _load_json(REGISTRY_FILE, [])


def hypothesis_key(strategy):
    basis = json.dumps({"family": strategy["family"], "params": strategy["params"],
                        "assets": sorted(strategy["assets"]),
                        "timeframe": strategy["timeframe"]}, sort_keys=True)
    return hashlib.sha256(basis.encode()).hexdigest()[:16]


def _registry_append(entry):
    reg = registry()
    reg.append(entry)
    with open(REGISTRY_FILE, "w") as f:
        json.dump(reg, f, indent=1, ensure_ascii=False)


def family_test_count(family):
    return sum(1 for e in registry() if e.get("family") == family)


def required_z(family=None):
    """Bonferroni GLOBAL à vie (audit 2026-06-17, P6) : la déflation porte sur le
    NOMBRE TOTAL de tests jamais soumis, PAS par famille — sinon tester la même
    idée sous une famille cousine (momentum / momentum_regime / momentum_breakout)
    remet le seuil à ~1.96. Inclut le test courant. (family gardé pour le rapport,
    plus utilisé comme compteur.)"""
    n = len(registry()) + 1
    alpha = BASE_ALPHA / n
    return NormalDist().inv_cdf(1 - alpha), alpha, n


# ── Simulation (coûts inclus, une position à la fois) ────────────────────────
def _session_of(ts_epoch):
    p = tz.to_paris(dt.datetime.fromtimestamp(ts_epoch, dt.timezone.utc))
    if p.weekday() >= 5:
        return "WEEKEND"
    if p.hour >= 23 or p.hour < 8:
        return "OVERNIGHT"
    return "SESSION"


def simulate(candles, signal_fn, exit_rule, asset, ctx_fn=None):
    """Backtest séquentiel sans lookahead.

    Décision sur le close de la bougie i, entrée à l'OPEN de i+1.
    SL prioritaire si SL et TP touchés dans la même bougie (convention V1).
    Sortie à horizon au close, spread de sortie inclus. Swap par nuit.
    """
    stop_pct = float(exit_rule["stop_pct"])
    tp_pct = float(exit_rule["tp_pct"])
    horizon = int(exit_rule.get("horizon_bars", 32))
    trades = []
    pos = None

    for i in range(WARMUP_BARS, len(candles) - 1):
        bar = candles[i]
        if pos:
            sign = 1 if pos["dir"] == "LONG" else -1
            hi, lo = float(bar[2]), float(bar[3])
            session = _session_of(float(bar[0]))
            exit_price, kind = None, None
            sl_hit = lo <= pos["stop"] if sign > 0 else hi >= pos["stop"]
            tp_hit = hi >= pos["tp"] if sign > 0 else lo <= pos["tp"]
            if sl_hit:
                exit_price, kind = costs.adjust_exit(asset, pos["stop"], pos["dir"], session, "sl"), "SL"
            elif tp_hit:
                exit_price, kind = costs.adjust_exit(asset, pos["tp"], pos["dir"], session, "tp"), "TP"
            elif i - pos["i"] >= horizon:
                exit_price, kind = costs.adjust_exit(asset, float(bar[4]), pos["dir"], session, "market"), "TIME"
            if exit_price is not None:
                pnl = sign * (exit_price - pos["entry"]) / pos["entry"] * 100
                nights = costs.nights_held(
                    dt.datetime.fromtimestamp(pos["ts"], dt.timezone.utc).isoformat(),
                    dt.datetime.fromtimestamp(float(bar[0]), dt.timezone.utc).isoformat())
                pnl -= costs.swap_pct(asset, nights)
                paris = tz.to_paris(dt.datetime.fromtimestamp(pos["ts"], dt.timezone.utc))
                trades.append({"pnl_pct": round(pnl, 4), "kind": kind, "dir": pos["dir"],
                               "paris": paris.strftime("%Y-%m-%d %H:%M"), "asset": asset})
                pos = None
            continue

        window = candles[max(0, i - 400):i + 1]
        ctx = ctx_fn(float(bar[0])) if ctx_fn else None
        sig = signal_fn(window, ctx)
        if sig in ("LONG", "SHORT"):
            sign = 1 if sig == "LONG" else -1
            entry_session = _session_of(float(candles[i + 1][0]))
            if entry_session == "WEEKEND":
                continue  # marché fermé : aucune entrée sur une bougie week-end (hygiène échantillon, analyse 06-19)
            raw = float(candles[i + 1][1])  # open de la bougie suivante (entrée MARKET)
            # Entrée market : on paie le spread à l'entrée AUSSI (sinon coûts ÷2, audit 06-18).
            entry = costs.adjust_entry(asset, raw, sig, entry_session)
            # Stop/TP restent aux niveaux INTENTIONNELS (relatifs au prix signal brut).
            pos = {"dir": sig, "entry": entry, "i": i + 1, "ts": float(candles[i + 1][0]),
                   "stop": raw * (1 - sign * stop_pct / 100),
                   "tp": raw * (1 + sign * tp_pct / 100)}
    return trades


# ── Incertitude (autosuffisante, déterministe) ───────────────────────────────
def bootstrap_ci_by_day(trades, iters=BOOT_ITERS, seed=42):
    days = {}
    for t in trades:
        days.setdefault(t["paris"][:10], []).append(t["pnl_pct"])
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
    return (round(means[int(0.025 * iters)], 4), round(means[int(0.975 * iters) - 1], 4))


def _tstat(pnls):
    n = len(pnls)
    if n < 2:
        return 0.0
    mean = sum(pnls) / n
    var = sum((x - mean) ** 2 for x in pnls) / (n - 1)
    se = math.sqrt(var / n) if var > 0 else 0.0
    return mean / se if se > 0 else 0.0


def _daily_means(trades):
    """Moyennes JOURNALIÈRES de pnl (audit P5) : le t-stat doit se calculer sur
    les JOURS (blocs indépendants), pas par trade — l'autocorrélation intraday
    (~5,6 min) gonfle un t par-trade. Cohérent avec bootstrap_ci_by_day."""
    days = {}
    for t in trades:
        days.setdefault(t["paris"][:10], []).append(t["pnl_pct"])
    return [sum(v) / len(v) for v in days.values()]


# ── Walk-forward + verdict ───────────────────────────────────────────────────
def _windows(candles, timeframe):
    """4 blocs chronologiques ; fenêtres de test = blocs 2,3,4 avec purge."""
    purge = PURGE_BARS.get(timeframe, 24)
    n = len(candles)
    bounds = [int(n * q / 4) for q in range(5)]
    wins = []
    for w in range(1, 4):
        start = bounds[w] + purge
        end = bounds[w + 1]
        if end - start > WARMUP_BARS + 10:
            # le warmup vient des bougies AVANT la fenêtre (déjà connues)
            wins.append((max(0, start - WARMUP_BARS - 1), start, end))
    return wins


def evaluate(strategy, data, sources=None, ctx_fn=None):
    """Le verdict. strategy = {id, hypothesis_text, family, params, exit_rule,
    assets, timeframe[, variant_of]}. data = {asset: candles}.
    sources = {asset: "yfinance"|"tradingview"|...} pour la garde anti-basis.
    """
    sid = strategy["id"]
    family = strategy["family"]
    hkey = hypothesis_key(strategy)

    # Doublon : déjà testé → refus sauf variante déclarée
    for e in registry():
        if e.get("hypothesis_key") == hkey:
            return {"verdict": "DUPLICATE", "id": sid,
                    "note": f"hypothèse déjà testée le {e.get('ts','?')[:10]} ({e.get('id')})"}

    # Garde anti-basis : une seule source par test
    if sources and len(set(sources.values())) > 1:
        return {"verdict": "INVALID", "id": sid,
                "note": f"sources hétérogènes {sources} — interdit (basis)"}

    z_req, alpha, n_family = required_z(family)
    signal_fn = strategy_families.build_signal(family, strategy["params"])

    # Le segment de chaque fenêtre démarre WARMUP_BARS avant son début et
    # simulate() n'ouvre aucune position avant WARMUP_BARS : tous les trades
    # entrent donc DANS la fenêtre de test, jamais avant (pas de fuite).
    window_stats = []
    test_trades = []
    for w_idx in range(N_WINDOWS):
        w_trades = []
        for asset, candles in data.items():
            wins = _windows(candles, strategy["timeframe"])
            if w_idx >= len(wins):
                continue
            w0, start, end = wins[w_idx]
            seg = candles[w0:end]
            w_trades.extend(simulate(seg, signal_fn, strategy["exit_rule"], asset, ctx_fn=ctx_fn))
        window_stats.append(w_trades)
        test_trades.extend(w_trades)

    per_window = []
    for w_trades in window_stats:
        n = len(w_trades)
        exp = sum(t["pnl_pct"] for t in w_trades) / n if n else 0.0
        per_window.append({"n": n, "exp": round(exp, 4), "positive": n > 0 and exp > 0})

    pnls = [t["pnl_pct"] for t in test_trades]
    n_eff = len(pnls)
    exp = sum(pnls) / n_eff if n_eff else 0.0
    ci = bootstrap_ci_by_day(test_trades)
    t_stat = _tstat(_daily_means(test_trades))  # par JOUR, pas par trade (audit P5)
    windows_pos = sum(1 for w in per_window if w["positive"])

    checks = {
        "n_eff_ge_30": n_eff >= MIN_EFF_N,
        "windows_pos_ge_2of3": windows_pos >= MIN_WINDOWS_POS,
        "ci_low_gt_0": bool(ci and ci[0] > 0),
        "tstat_ge_z_deflated": t_stat >= z_req,
    }
    verdict = "PAPER" if all(checks.values()) else "KILLED"

    strategy_hash = hashlib.sha256(json.dumps(
        {k: strategy[k] for k in ("id", "family", "params", "exit_rule", "assets", "timeframe")},
        sort_keys=True).encode()).hexdigest()
    harness_hash = hashlib.sha256(open(__file__, "rb").read()).hexdigest()

    report = {
        "id": sid, "verdict": verdict, "family": family,
        "hypothesis_key": hkey,
        "hypothesis_text": strategy.get("hypothesis_text", ""),
        "params": strategy["params"], "exit_rule": strategy["exit_rule"],
        "assets": strategy["assets"], "timeframe": strategy["timeframe"],
        "n_eff": n_eff, "expectancy_net": round(exp, 4),
        "ci95_bootstrap_days": ci, "t_stat": round(t_stat, 3),
        "z_required": round(z_req, 3), "alpha_deflated": alpha,
        "family_tests_lifetime": n_family,
        "per_window": per_window, "checks": checks,
        "strategy_hash": strategy_hash, "harness_hash": harness_hash,
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    os.makedirs(VERDICTS_DIR, exist_ok=True)
    with open(os.path.join(VERDICTS_DIR, f"{sid}.json"), "w") as f:
        json.dump(report, f, indent=1, ensure_ascii=False)
    _registry_append({"id": sid, "hypothesis_key": hkey, "family": family,
                      "verdict": verdict, "variant_of": strategy.get("variant_of"),
                      "ts": report["ts"]})

    if verdict == "PAPER":
        papers = _load_json(PAPER_FILE, [])
        papers.append({"id": sid, "family": family, "params": strategy["params"],
                       "exit_rule": strategy["exit_rule"], "assets": strategy["assets"],
                       "timeframe": strategy["timeframe"], "status": "PAPER",
                       "since": report["ts"], "strategy_hash": strategy_hash})
        with open(PAPER_FILE, "w") as f:
            json.dump(papers, f, indent=1, ensure_ascii=False)

    return report


# ── Rétrogradation automatique ───────────────────────────────────────────────
def check_demotions(journal_dict):
    """Borne HAUTE de l'IC < 0 sur les 30 derniers trades effectifs d'une
    stratégie PAPER → KILLED, sans demander. Appelé par le watcher (lecture
    journal uniquement)."""
    papers = _load_json(PAPER_FILE, [])
    if not papers:
        return []
    demoted = []
    for p in papers:
        if p.get("status") != "PAPER":
            continue
        trader = f"PAPER_{p['id']}"
        rows = [s for s in journal_dict.get("signals", [])
                if s.get("trader") == trader and s.get("status") == "CLOSED"
                and s.get("pnl_pct") is not None]
        rows = rows[-DEMOTE_WINDOW:]
        if len(rows) < DEMOTE_WINDOW:
            continue
        ci = bootstrap_ci_by_day([{"paris": s.get("paris", ""), "pnl_pct": s["pnl_pct"]}
                                  for s in rows])
        if ci and ci[1] < 0:
            p["status"] = "KILLED"
            p["killed_ts"] = dt.datetime.now(dt.timezone.utc).isoformat()
            p["killed_reason"] = f"IC95 haute {ci[1]} < 0 sur {len(rows)} trades"
            demoted.append(p["id"])
    if demoted:
        with open(PAPER_FILE, "w") as f:
            json.dump(papers, f, indent=1, ensure_ascii=False)
    return demoted


def lab_counters():
    reg = registry()
    papers = _load_json(PAPER_FILE, [])
    return {
        "testees": len(reg),
        "tuees": sum(1 for e in reg if e.get("verdict") == "KILLED"),
        "papier": sum(1 for p in papers if p.get("status") == "PAPER"),
        "promues": sum(1 for p in papers if p.get("status") == "LIVE"),
    }


if __name__ == "__main__":
    print(json.dumps(lab_counters(), ensure_ascii=False))
    z, a, n = required_z("momentum")
    print(f"momentum: test n°{n}, alpha déflaté {a:.4f}, z requis {z:.2f}")
