#!/usr/bin/env python3
"""DATAFEED, interface unique prix/bougies avec chaîne de fallback.

Problème : tout reposait sur le websocket TradingView non officiel, qui peut
casser sans préavis et n'a pas de volume réel pour les CFD. Ici :

  get_price(asset)            primaire TradingView WS → yfinance → cache (stale)
  get_candles(asset, tf, n)   idem

Chaque réponse porte `source` et `latency_ms` ; si la donnée vient du cache,
`stale: true`. Le watcher logge la source utilisée à chaque cycle via
last_sources().

Sous-jacents réels : GOLD ↔ futures COMEX GC, US500 ↔ futures CME ES, c'est
là qu'existent le volume réel et le carnet. ATTENTION basis : GC=F et ES=F
cotent au-dessus du spot/CFD (contango). Tant que les niveaux d'entrée/stop
des signaux sont posés sur les prix TradingView, le fallback yfinance sert à
la CONTINUITÉ (panne TV), pas à mélanger les référentiels : tout consommateur
doit vérifier `source` avant de comparer des niveaux absolus.
"""

import datetime as dt
import json
import os
import time

CACHE_FILE = "/Users/sam/trading/datafeed_cache.json"

ASSET_MAP = {
    #          TradingView (via tv_candles.SYMBOL_MAP)   yfinance (réel/futures)
    "GOLD":   {"yf": "GC=F",      "yf_alt": "XAUUSD=X"},
    "US500":  {"yf": "ES=F",      "yf_alt": "^GSPC"},
    "NAS100": {"yf": "NQ=F",      "yf_alt": "^NDX"},
    "VIX":    {"yf": "^VIX"},
    "DXY":    {"yf": "DX-Y.NYB"},
    "OIL":    {"yf": "CL=F"},
    "BTC":    {"yf": "BTC-USD"},
    "ETH":    {"yf": "ETH-USD"},
}

YF_TF = {"1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", "1h": "60m", "1d": "1d"}
YF_PERIOD = {"1m": "5d", "5m": "1mo", "15m": "1mo", "30m": "1mo", "1h": "3mo", "1d": "2y"}

_last_sources = {}  # {"GOLD:price": "tradingview", "US500:candles:1m": "yfinance", ...}

# Yahoo rate-limite aussi : si TradingView tombe durablement, le watcher à
# 5 min ne doit pas marteler yfinance. 60 s minimum entre deux appels réseau
# PAR CLÉ (asset, kind), un throttle global affamerait le backfill, qui a
# besoin de plusieurs actifs dans le même cycle. La fenêtre n'est consommée
# que sur appel réussi (un échec ne brûle pas la minute).
YF_MIN_INTERVAL_S = 60
_yf_last_ok = {}  # (asset, kind) → epoch du dernier appel réussi


def _yf_allowed(asset, kind):
    return time.time() - _yf_last_ok.get((asset, kind), 0.0) >= YF_MIN_INTERVAL_S


def _yf_mark(asset, kind):
    _yf_last_ok[(asset, kind)] = time.time()


def last_sources():
    """Sources utilisées depuis le début du process (pour le log du watcher)."""
    return dict(_last_sources)


def _load_cache():
    try:
        with open(CACHE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cache(cache):
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f)
    except Exception:
        pass


def _remember(kind, asset, payload):
    cache = _load_cache()
    cache[f"{asset}:{kind}"] = payload
    _save_cache(cache)


def _from_cache(kind, asset):
    payload = _load_cache().get(f"{asset}:{kind}")
    if not payload:
        return None
    payload = dict(payload)
    payload["stale"] = True
    payload["source"] = payload.get("source", "?") + "+cache"
    return payload


# ── Sources prix ─────────────────────────────────────────────────────────────
def _tv_price(asset, timeout=14):
    from tv_live import TVLiveClient
    from tv_candles import SYMBOL_MAP
    sym = SYMBOL_MAP.get(asset)
    if not sym:
        return None
    raw = TVLiveClient(symbols=[sym], timeout=timeout).fetch()
    d = raw.get(sym.split(":")[-1])
    if not d or d.get("lp") is None:
        return None
    return {"lp": d["lp"], "high_price": d.get("high_price"), "low_price": d.get("low_price")}


def _yf_price(asset):
    if not _yf_allowed(asset, "price"):
        return None
    import yfinance as yf
    conf = ASSET_MAP.get(asset) or {}
    for key in ("yf", "yf_alt"):
        ticker = conf.get(key)
        if not ticker:
            continue
        try:
            info = yf.Ticker(ticker).fast_info
            lp = info.last_price
            if lp:
                _yf_mark(asset, "price")
                return {"lp": round(float(lp), 4),
                        "high_price": float(info.day_high) if info.day_high else None,
                        "low_price": float(info.day_low) if info.day_low else None,
                        "yf_ticker": ticker}
        except Exception:
            continue
    return None


def get_price(asset):
    """Prix courant avec fallback. {lp, source, latency_ms, stale, ts, ...}"""
    for name, fn in (("tradingview", _tv_price), ("yfinance", _yf_price)):
        t0 = time.time()
        try:
            d = fn(asset)
        except Exception:
            d = None
        if d:
            d.update({"source": name, "latency_ms": int((time.time() - t0) * 1000),
                      "stale": False, "ts": dt.datetime.now(dt.timezone.utc).isoformat()})
            _last_sources[f"{asset}:price"] = name
            _remember("price", asset, d)
            return d
    cached = _from_cache("price", asset)
    if cached:
        _last_sources[f"{asset}:price"] = cached["source"]
        return cached
    return None


# ── Sources bougies ──────────────────────────────────────────────────────────
def _tv_candles(asset, tf, n, timeout=28):
    from tv_candles import TVCandleClient
    bars = TVCandleClient(symbols=[asset], timeframe=tf, n_bars=n,
                          timeout=timeout).fetch_candles().get(asset) or []
    return bars or None


def _yf_candles(asset, tf, n):
    if not _yf_allowed(asset, f"candles:{tf}"):
        return None
    import yfinance as yf
    interval = YF_TF.get(tf)
    conf = ASSET_MAP.get(asset) or {}
    if not interval:
        return None
    for key in ("yf", "yf_alt"):
        ticker = conf.get(key)
        if not ticker:
            continue
        try:
            df = yf.Ticker(ticker).history(period=YF_PERIOD.get(tf, "5d"),
                                           interval=interval)
            if df is None or df.empty:
                continue
            df = df.tail(n)
            _yf_mark(asset, f"candles:{tf}")
            return [[ts.timestamp(), float(r["Open"]), float(r["High"]),
                     float(r["Low"]), float(r["Close"]), float(r.get("Volume") or 0)]
                    for ts, r in df.iterrows()]
        except Exception:
            continue
    return None


def get_candles(asset, tf="1m", n=100):
    """Bougies [ts,o,h,l,c,v] avec fallback. {candles, source, latency_ms, stale}"""
    for name, fn in (("tradingview", _tv_candles), ("yfinance", _yf_candles)):
        t0 = time.time()
        try:
            bars = fn(asset, tf, n)
        except Exception:
            bars = None
        if bars:
            out = {"candles": bars, "source": name,
                   "latency_ms": int((time.time() - t0) * 1000), "stale": False,
                   "ts": dt.datetime.now(dt.timezone.utc).isoformat()}
            _last_sources[f"{asset}:candles:{tf}"] = name
            # Cache borné : les 400 dernières bougies suffisent au fallback
            _remember(f"candles:{tf}", asset, dict(out, candles=bars[-400:]))
            return out
    cached = _from_cache(f"candles:{tf}", asset)
    if cached:
        _last_sources[f"{asset}:candles:{tf}"] = cached["source"]
        return cached
    return None


if __name__ == "__main__":
    for asset in ("GOLD", "US500"):
        p = get_price(asset)
        print(f"{asset} prix   : {p['lp']} [{p['source']} {p['latency_ms']}ms stale={p['stale']}]" if p else f"{asset}: AUCUNE SOURCE")
        c = get_candles(asset, "1m", 10)
        if c:
            print(f"{asset} bougies: {len(c['candles'])} x1m [{c['source']} {c['latency_ms']}ms] dernière={c['candles'][-1][4]}")
