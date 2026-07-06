#!/usr/bin/env python3
"""CRYPTO PULSE — capteur risk-on/risk-off intraday via microstructure BTC.

Imbalance du carnet (top 5 niveaux) + delta des agressions sur 5 min.
BTC réagit en continu (24/7) : en régime risk-off, sa corrélation avec ES
monte, ce qui en fait un thermomètre utile quand les indices sont fermés.

Note d'implémentation : le MCP Revolut X (carnet L2 natif) n'est accessible
que dans le chat Claude, pas depuis ce process autonome. On lit donc la même
microstructure sur l'API publique Binance (sans clé, gratuit). Si Sam trade
BTC/ETH sur Revolut X, le MCP reste l'outil interactif pour SON carnet.

Alimente btc_imbalance / btc_delta_5m / crypto_risk dans le feature store.
"""

import datetime as dt
import json
import time
import urllib.request

API = "https://api.binance.com/api/v3"
SYMBOL = "BTCUSDT"
DEPTH_LEVELS = 5
TRADES_WINDOW_S = 300
CACHE_TTL_S = 60  # un cycle watcher = 5 min ; inutile d'appeler plus d'1x/min

_cache = {"ts": 0.0, "snap": None}


def _get(url, timeout=12):
    req = urllib.request.Request(url, headers={"User-Agent": "crypto-pulse/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def book_imbalance(levels=DEPTH_LEVELS):
    """(volume bid - volume ask) / total sur les top niveaux. [-1, +1]."""
    d = _get(f"{API}/depth?symbol={SYMBOL}&limit={max(levels, 5)}")
    bid = sum(float(q) for _, q in d["bids"][:levels])
    ask = sum(float(q) for _, q in d["asks"][:levels])
    total = bid + ask
    return round((bid - ask) / total, 3) if total else 0.0


def trade_delta(window_s=TRADES_WINDOW_S):
    """Delta des agressions (achat - vente) normalisé sur la fenêtre. [-1, +1].

    Binance aggTrades : m=True → l'acheteur est maker → agression VENDEUSE.
    On demande les 1000 trades les PLUS RÉCENTS (sans bornes : avec
    startTime/endTime l'API renvoie les 1000 premiers de la fenêtre, donc en
    période active on mesurait le début d'il y a 5 min, pas l'agression
    courante) et on filtre sur la fenêtre côté Python.
    """
    start_ms = int((time.time() - window_s) * 1000)
    trades = _get(f"{API}/aggTrades?symbol={SYMBOL}&limit=1000")
    recent = [t for t in trades if t["T"] >= start_ms]
    buy = sum(float(t["q"]) for t in recent if not t["m"])
    sell = sum(float(t["q"]) for t in recent if t["m"])
    total = buy + sell
    return round((buy - sell) / total, 3) if total else 0.0


def snapshot():
    """{btc_imbalance, btc_delta_5m, crypto_risk, ts} — cache 60 s, None si API down."""
    if time.time() - _cache["ts"] < CACHE_TTL_S and _cache["snap"]:
        return _cache["snap"]
    try:
        imb = book_imbalance()
        delta = trade_delta()
    except Exception:
        return _cache["snap"]  # dernier connu (ou None au premier appel)
    if imb > 0.15 and delta > 0.1:
        risk = "RISK_ON"
    elif imb < -0.15 and delta < -0.1:
        risk = "RISK_OFF"
    else:
        risk = "NEUTRAL"
    snap = {"btc_imbalance": imb, "btc_delta_5m": delta, "crypto_risk": risk,
            "ts": dt.datetime.now(dt.timezone.utc).isoformat()}
    _cache.update(ts=time.time(), snap=snap)
    return snap


if __name__ == "__main__":
    s = snapshot()
    if s:
        print(f"BTC imbalance carnet (top {DEPTH_LEVELS}): {s['btc_imbalance']:+.3f} | "
              f"delta agressions 5min: {s['btc_delta_5m']:+.3f} → {s['crypto_risk']}")
    else:
        print("API Binance indisponible")
